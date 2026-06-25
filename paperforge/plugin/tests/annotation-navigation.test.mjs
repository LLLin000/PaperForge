/**
 * Vitest tests for PDF jump-target navigation helpers.
 *
 * Pure, side-effect-free helpers for canonical vault-relative path extraction,
 * paper PDF candidate building, and annotation PDF target resolution.
 *
 * Contracts enforced: D-04 through D-08 and D-11.
 */
import { describe, it, expect } from 'vitest';

const {
    extractVaultPdfPath,
    buildPaperPdfCandidates,
    resolveAnnotationPdfTarget,
} = await import('../src/testable.js');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const ATTACH_KEY_A = 'ATTACH_A';
const ATTACH_KEY_B = 'ATTACH_B';
const STORAGE_KEY = 'STORAGE_ABC';

/** A minimal paper entry with pdf_path in wikilink form. */
function makeEntry(overrides = {}) {
    return {
        pdf_path: '[[99_System/Zotero/storage/STORAGE_ABC/main.pdf]]',
        zotero_storage_key: STORAGE_KEY,
        supplementary: [],
        ...overrides,
    };
}

/** A normalized annotation row with pdfLocation and provenance. */
function makeAnnotationRow(overrides = {}) {
    return {
        display: { page: 0, pageLabel: '1', type: 'highlight', color: '#ffd400', selectedText: 'test', comment: '' },
        provenance: {
            source: 'zotero',
            sourceAttachmentKey: ATTACH_KEY_A,
            sourceAnnotationKey: 'ANNOT_1',
        },
        pdfLocation: {
            pageIndex: 0,
            pageLabel: '1',
            sourceAttachmentKey: ATTACH_KEY_A,
            positionJson: '{}',
            selectorJson: '{}',
            sortIndex: 0,
            rowId: 'r1',
        },
        raw: {},
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// extractVaultPdfPath — wikilink unwrapping and path validation per D-05
// ---------------------------------------------------------------------------

describe('extractVaultPdfPath', () => {
    it('unwraps a canonical vault-relative wikilink to a clean path', () => {
        const result = extractVaultPdfPath('[[99_System/Zotero/storage/K/file.pdf]]');
        expect(result).toEqual({
            ok: true,
            path: '99_System/Zotero/storage/K/file.pdf',
            reason: null,
        });
    });

    it('rejects an absolute Windows path', () => {
        const result = extractVaultPdfPath('D:\\Zotero\\storage\\K\\file.pdf');
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
        expect(result.reason).toBeTruthy();
    });

    it('rejects a URI scheme path', () => {
        const result = extractVaultPdfPath('file:///Zotero/storage/K/file.pdf');
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('rejects a path with directory traversal', () => {
        const result = extractVaultPdfPath('[[../../vault/evil.pdf]]');
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('rejects a non-PDF file extension', () => {
        const result = extractVaultPdfPath('[[99_System/Zotero/storage/K/file.txt]]');
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('rejects a raw storage: value without wikilink', () => {
        const result = extractVaultPdfPath('storage:KEY/file.pdf');
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('rejects a bare relative path without wikilink', () => {
        const result = extractVaultPdfPath('KEY/file.pdf');
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('rejects a malformed wikilink (missing closing brackets)', () => {
        const result = extractVaultPdfPath('[[99_System/file.pdf');
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('rejects null input', () => {
        const result = extractVaultPdfPath(null);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('rejects non-string input', () => {
        const result = extractVaultPdfPath(42);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('returns a stable non-sensitive reason string on rejection', () => {
        const result = extractVaultPdfPath('D:\\bad\\path.pdf');
        expect(typeof result.reason).toBe('string');
        expect(result.reason).not.toContain('D:\\');
        expect(result.reason).not.toContain('\\bad\\');
    });

    it('accepts a wikilink without subdirectory prefix', () => {
        const result = extractVaultPdfPath('[[file.pdf]]');
        expect(result.ok).toBe(true);
        expect(result.path).toBe('file.pdf');
    });

    it('accepts a wikilink with a deep vault path', () => {
        const result = extractVaultPdfPath('[[a/b/c/d/e/f/file.pdf]]');
        expect(result.ok).toBe(true);
        expect(result.path).toBe('a/b/c/d/e/f/file.pdf');
    });
});

// ---------------------------------------------------------------------------
// buildPaperPdfCandidates — canonical candidate extraction from entry metadata
// ---------------------------------------------------------------------------

describe('buildPaperPdfCandidates', () => {
    it('extracts the main pdf_path as the first candidate with an attachment key', () => {
        const entry = makeEntry();
        const candidates = buildPaperPdfCandidates(entry);
        expect(candidates.length).toBeGreaterThanOrEqual(1);
        const main = candidates[0];
        expect(main.path).toBe('99_System/Zotero/storage/STORAGE_ABC/main.pdf');
        // The main PDF's attachment key should be derived from the storage key
        expect(main.attachmentKey).toBeTruthy();
    });

    it('includes supplementary PDFs as additional candidates', () => {
        const entry = makeEntry({
            supplementary: [
                '[[99_System/Zotero/storage/STORAGE_ABC/supp1.pdf]]',
                '[[99_System/Zotero/storage/STORAGE_ABC/supp2.pdf]]',
            ],
        });
        const candidates = buildPaperPdfCandidates(entry);
        expect(candidates.length).toBe(3);
        const suppPaths = candidates.map(c => c.path);
        expect(suppPaths).toContain('99_System/Zotero/storage/STORAGE_ABC/supp1.pdf');
        expect(suppPaths).toContain('99_System/Zotero/storage/STORAGE_ABC/supp2.pdf');
    });

    it('deduplicates candidates by path', () => {
        const entry = makeEntry({
            pdf_path: '[[99_System/Zotero/storage/K/dup.pdf]]',
            supplementary: ['[[99_System/Zotero/storage/K/dup.pdf]]'],
        });
        const candidates = buildPaperPdfCandidates(entry);
        const paths = candidates.map(c => c.path);
        const uniquePaths = [...new Set(paths)];
        expect(paths.length).toBe(uniquePaths.length);
    });

    it('skips entries where pdf_path fails path extraction', () => {
        const entry = makeEntry({ pdf_path: null });
        const candidates = buildPaperPdfCandidates(entry);
        expect(Array.isArray(candidates)).toBe(true);
    });

    it('returns empty array for null entry', () => {
        const candidates = buildPaperPdfCandidates(null);
        expect(candidates).toEqual([]);
    });

    it('returns empty array for undefined entry', () => {
        const candidates = buildPaperPdfCandidates(undefined);
        expect(candidates).toEqual([]);
    });

    it('derives attachment key from zotero_storage_key when pdf_path is in storage', () => {
        const entry = makeEntry({
            pdf_path: '[[99_System/Zotero/storage/STORAGE_ABC/main.pdf]]',
            zotero_storage_key: 'STORAGE_ABC',
        });
        const candidates = buildPaperPdfCandidates(entry);
        expect(candidates[0].attachmentKey).toBe('STORAGE_ABC');
    });

    it('includes supplementary candidates with correct attachment keys', () => {
        const entry = makeEntry({
            supplementary: ['[[99_System/Zotero/storage/STORAGE_ABC/supp.pdf]]'],
        });
        const candidates = buildPaperPdfCandidates(entry);
        const supp = candidates.find(c => c.path.includes('supp.pdf'));
        expect(supp).toBeTruthy();
        expect(supp.attachmentKey).toBeTruthy();
    });

    it('does not mutate the input entry object', () => {
        const entry = makeEntry();
        const frozen = JSON.stringify(entry);
        buildPaperPdfCandidates(entry);
        expect(JSON.stringify(entry)).toBe(frozen);
    });
});

// ---------------------------------------------------------------------------
// resolveAnnotationPdfTarget — full resolution logic per D-04 through D-07
// ---------------------------------------------------------------------------

const entryMainOnly = makeEntry();
const entryWithSupp = makeEntry({
    supplementary: ['[[99_System/Zotero/storage/STORAGE_ABC/supp1.pdf]]'],
});

describe('resolveAnnotationPdfTarget — exact identity match (D-04)', () => {
    it('resolves when sourceAttachmentKey matches a candidate attachmentKey', () => {
        const row = makeAnnotationRow();
        // Match against the main PDF which has attachmentKey derived from storage
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.path).toBeTruthy();
        expect(typeof result.path).toBe('string');
    });

    it('returns ok with path, page, and linkText on exact match', () => {
        const row = makeAnnotationRow();
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.path).toBeTruthy();
        expect(result.page).toBe(1); // pageIndex 0 → page 1
        expect(result.linkText).toContain('#page=');
    });
});

describe('resolveAnnotationPdfTarget — identity mismatch (D-07)', () => {
    it('returns ok: false with no path when identity does not match any candidate', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: 'NONEXISTENT_KEY', pageIndex: 0, pageLabel: '1' },
            provenance: { sourceAttachmentKey: 'NONEXISTENT_KEY' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
        expect(result.reason).toBeTruthy();
    });

    it('provides a stable non-sensitive reason for mismatch', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: 'UNKNOWN', pageIndex: 0, pageLabel: '1' },
            provenance: { sourceAttachmentKey: 'UNKNOWN' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.reason).toBeTruthy();
        expect(result.reason).not.toContain('UNKNOWN');
        expect(result.reason).not.toContain('NONEXISTENT');
    });

    it('never silently falls back to main PDF on mismatch', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: 'MISMATCH', pageIndex: 0, pageLabel: '1' },
            provenance: { sourceAttachmentKey: 'MISMATCH' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });
});

describe('resolveAnnotationPdfTarget — no identity / single-candidate fallback (D-06)', () => {
    it('resolves when no attachment identity exists and entry has exactly one candidate', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: null, pageIndex: 0, pageLabel: '1' },
            provenance: { sourceAttachmentKey: null },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.path).toBeTruthy();
    });

    it('fails closed when no identity and entry has multiple candidates (ambiguity)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: null, pageIndex: 0, pageLabel: '1' },
            provenance: { sourceAttachmentKey: null },
        });
        const result = resolveAnnotationPdfTarget(row, entryWithSupp);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('fails closed when no identity and entry has zero valid candidates', () => {
        const emptyEntry = makeEntry({ pdf_path: null, supplementary: [] });
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: null, pageIndex: 0, pageLabel: '1' },
            provenance: { sourceAttachmentKey: null },
        });
        const result = resolveAnnotationPdfTarget(row, emptyEntry);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });
});

describe('resolveAnnotationPdfTarget — page conversion (D-08)', () => {
    it('converts pageIndex 0 to page 1', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: 0, pageLabel: '1' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.page).toBe(1);
    });

    it('converts pageIndex 2 to page 3', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: 2, pageLabel: '3' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.page).toBe(3);
    });

    it('creates correct linkText with page number', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: 2, pageLabel: '3' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.linkText).toContain('#page=3');
        expect(result.linkText).toContain(result.path);
    });

    it('returns page=null for negative pageIndex (D-11)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: -1, pageLabel: '' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true); // PDF still resolved
        expect(result.path).toBeTruthy();
        expect(result.page).toBeNull();
    });

    it('returns page=null for fractional pageIndex (D-11)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: 1.5, pageLabel: '' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.page).toBeNull();
    });

    it('returns page=null for string pageIndex (D-11)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: '3', pageLabel: '' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.page).toBeNull();
    });

    it('returns page=null for null pageIndex (D-11)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: null, pageLabel: '' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.page).toBeNull();
    });

    it('returns page=null for missing pageIndex (D-11)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageLabel: '' },
            // pageIndex intentionally omitted
        });
        // Remove pageIndex from pdfLocation
        delete row.pdfLocation.pageIndex;
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.page).toBeNull();
    });

    it('provides a stable page-degraded reason when page is invalid (D-11)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: null, pageLabel: '' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(true);
        expect(result.reason).toBeTruthy();
        // Reason must not contain raw input values
        expect(result.reason).not.toContain('null');
        expect(result.reason).toBeTruthy();
    });

    it('does not use pageLabel for arithmetic', () => {
        // pageLabel should not be used for computation, only pageIndex
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: 5, pageLabel: 'VII' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        // Must use pageIndex, not pageLabel
        expect(result.page).toBe(6);
        expect(result.page).not.toBe(7); // VII would be 7 if used
    });
});

describe('resolveAnnotationPdfTarget — result shape', () => {
    it('returns ok, path, page, linkText, and reason fields', () => {
        const row = makeAnnotationRow();
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result).toHaveProperty('ok');
        expect(result).toHaveProperty('path');
        expect(result).toHaveProperty('page');
        expect(result).toHaveProperty('linkText');
        expect(result).toHaveProperty('reason');
    });

    it('returns linkText as just path when page is null (plain-PDF target per D-11)', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_A, pageIndex: null, pageLabel: '' },
        });
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.linkText).toBe(result.path);
    });

    it('does not mutate the input row or entry', () => {
        const row = makeAnnotationRow();
        const entry = makeEntry();
        const rowFrozen = JSON.stringify(row);
        const entryFrozen = JSON.stringify(entry);
        resolveAnnotationPdfTarget(row, entry);
        expect(JSON.stringify(row)).toBe(rowFrozen);
        expect(JSON.stringify(entry)).toBe(entryFrozen);
    });
});

describe('resolveAnnotationPdfTarget — edge cases', () => {
    it('returns ok: false for null row', () => {
        const result = resolveAnnotationPdfTarget(null, entryMainOnly);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('returns ok: false for null entry', () => {
        const row = makeAnnotationRow();
        const result = resolveAnnotationPdfTarget(row, null);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('returns ok: false for row missing pdfLocation', () => {
        const row = makeAnnotationRow();
        delete row.pdfLocation;
        const result = resolveAnnotationPdfTarget(row, entryMainOnly);
        expect(result.ok).toBe(false);
        expect(result.path).toBeNull();
    });

    it('provides stable reason for every fail-closed case', () => {
        const cases = [
            { row: null, entry: entryMainOnly },
            { row: makeAnnotationRow(), entry: null },
        ];
        for (const c of cases) {
            const result = resolveAnnotationPdfTarget(c.row, c.entry);
            expect(result.reason).toBeTruthy();
            expect(typeof result.reason).toBe('string');
        }
    });
});
