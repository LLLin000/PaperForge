/**
 * Pure source surface selection, text normalization, and block shaping
 * (Phase ANN12, Plan 01).
 *
 * Pure CommonJS helpers for selecting PaperForge-owned reading source
 * content and preparing it for anchor resolution.  No fs, no Obsidian,
 * no native PDF DOM selectors/classes, no innerHTML, no subprocess.
 *
 * Source priority per D-01, D-02, D-03:
 *   1. Usable fulltext from `entry.fulltext_path`.
 *   2. Usable note body from `entry.note_path`.
 *   3. Explicit source-unavailable model with clear diagnostics.
 *
 * @module canvas/surface
 */

// ── Source constants ──

/**
 * Kinds of PaperForge-owned source content.
 *
 * @enum {string}
 * @readonly
 */
const SOURCE_KINDS = Object.freeze({
    FULLTEXT: 'fulltext',
    NOTE: 'note',
});

/**
 * Source model states.
 *
 * @enum {string}
 * @readonly
 */
const SOURCE_STATES = Object.freeze({
    READY: 'ready',
    UNAVAILABLE: 'source-unavailable',
});

// ── Page marker regex ──

/**
 * Matches OCR page markers like `<!-- page 1 -->`.
 * @private
 */
const _PAGE_MARKER_RE = /<!--\s*page\s+(\d+)\s*-->/gi;

// ── Source model builder ──

/**
 * Build a pure source model from the entry and already-read source inputs.
 *
 * Source priority per D-01, D-02, D-03:
 *   1. If `sourceInputs.fulltext` has readable text, use it (sourceKind=fulltext).
 *   2. Else if `sourceInputs.note` has readable text, use it (sourceKind=note)
 *      and record a fulltext miss in diagnostics.
 *   3. Otherwise return a source-unavailable model with a clear reason.
 *
 * Per D-17, the reason distinguishes missing-path vs missing/unreadable file
 * conditions when the caller supplies that information.
 *
 * The `sourceInputs` shape for both `fulltext` and `note`:
 *   { path: string|null, text: string|null, exists: boolean, readable: boolean, error?: string }
 *
 * @param {object} entry - Paper entry ({ key, fulltext_path?, note_path? }).
 * @param {object} sourceInputs - Runtime inputs ({ fulltext, note }).
 * @param {object} [options] - Optional flags (reserved for future use).
 * @returns {{ status: string, sourceKind: string|null, text: string|null,
 *            fulltextPath: string|null, notePath: string|null,
 *            diagnostics: object|null, reason: string|null }}
 */
function buildCanvasSourceModel(entry, sourceInputs, options) {
    const entryKey = firstNonBlank(entry && entry.key, entry && entry.zotero_key);

    // Extract paths from entry
    const ftPath = (entry && entry.fulltext_path) || null;
    const ntPath = (entry && entry.note_path) || null;

    // Extract runtime inputs
    const ftInput = (sourceInputs && sourceInputs.fulltext) || {};
    const ntInput = (sourceInputs && sourceInputs.note) || {};

    const ftText = ftInput.text || null;
    const ftReadable = Boolean(ftInput.readable) && ftText != null;
    const ntText = ntInput.text || null;
    const ntReadable = Boolean(ntInput.readable) && ntText != null;

    // Diagnostics object accumulates miss/reason info
    var diagnostics = {
        fulltext: {
            path: ftPath,
            exists: Boolean(ftInput.exists),
            readable: ftReadable,
            reason: null,
            miss: false,
        },
        note: {
            path: ntPath,
            exists: Boolean(ntInput.exists),
            readable: ntReadable,
            reason: null,
            miss: false,
        },
    };

    // ── Priority 1: usable fulltext ──
    if (ftReadable) {
        diagnostics.fulltext.reason = null;
        return {
            status: SOURCE_STATES.READY,
            sourceKind: SOURCE_KINDS.FULLTEXT,
            text: ftText,
            fulltextPath: ftPath,
            notePath: ntPath,
            diagnostics: diagnostics,
            paperKey: entryKey,
            reason: null,
        };
    }

    // ── Priority 2: usable note (fulltext unavailable) ──
    if (ntReadable) {
        // Compute fulltext miss reason
        var ftReason = _computeSourceUnavailableReason(ftPath, ftInput, 'fulltext');
        diagnostics.fulltext.reason = ftReason;
        diagnostics.fulltext.miss = true;

        return {
            status: SOURCE_STATES.READY,
            sourceKind: SOURCE_KINDS.NOTE,
            text: ntText,
            fulltextPath: ftPath,
            notePath: ntPath,
            diagnostics: diagnostics,
            paperKey: entryKey,
            reason: null,
        };
    }

    // ── Priority 3: source unavailable ──
    var ftReason2 = _computeSourceUnavailableReason(ftPath, ftInput, 'fulltext');
    var ntReason2 = _computeSourceUnavailableReason(ntPath, ntInput, 'note');

    diagnostics.fulltext.reason = ftReason2;
    diagnostics.fulltext.miss = true;
    diagnostics.note.reason = ntReason2;
    diagnostics.note.miss = true;

    // Build combined reason
    var combinedReason = '';
    if (ftReason2 && ntReason2) {
        combinedReason = ftReason2 + '; ' + ntReason2;
    } else if (ftReason2) {
        combinedReason = ftReason2;
    } else if (ntReason2) {
        combinedReason = ntReason2;
    } else {
        combinedReason = 'No source content is available for this paper.';
    }

    return {
        status: SOURCE_STATES.UNAVAILABLE,
        sourceKind: null,
        text: null,
        fulltextPath: ftPath,
        notePath: ntPath,
        diagnostics: diagnostics,
        paperKey: entryKey,
        reason: combinedReason,
    };
}

function firstNonBlank() {
    for (let i = 0; i < arguments.length; i++) {
        const value = arguments[i];
        if (value == null) continue;
        if (typeof value === 'string' && value.trim() === '') continue;
        return String(value);
    }
    return null;
}

/**
 * Compute a human-readable reason for why a source input is unavailable.
 * Distinguishes missing-path vs missing-file vs unreadable-file per D-17.
 *
 * Checks entry path first, then falls back to input path so callers can
 * supply path info via either channel.
 *
 * @param {string|null} path - Source path from entry.
 * @param {object} input - Source input ({ path, text, exists, readable, error }).
 * @param {'fulltext'|'note'} kind - Source kind label.
 * @returns {string|null} Reason string, or null if source is available.
 * @private
 */
function _computeSourceUnavailableReason(path, input, kind) {
    var label = kind === 'fulltext' ? 'Fulltext' : 'Note';
    var kindPrefix = kind === 'fulltext' ? 'fulltext' : 'note';

    // Use entry path first, then fall back to input path
    var effectivePath = path;
    if (effectivePath == null && input && input.path) {
        effectivePath = input.path;
    }

    // Path missing from both entry and input
    if (effectivePath == null) {
        return label + ' path is missing from the paper entry. (' + kindPrefix + '-path-missing)';
    }

    var exists = Boolean(input && input.exists);
    var readable = Boolean(input && input.readable);
    var error = (input && input.error) || null;

    if (!exists) {
        return label + ' file does not exist at: ' + effectivePath + ' (' + kindPrefix + '-file-missing)';
    }

    if (error) {
        return label + ' file is not readable: ' + error;
    }

    // File exists but no text content
    if (!readable) {
        return label + ' file has no readable content. (' + kindPrefix + '-file-missing)';
    }

    return null;
}

// ── Source block shaping ──

/**
 * Build page-shaped source blocks from OCR page-marker text.
 *
 * Splits the source text on `<!-- page N -->` markers (matching OCR
 * fulltext.md format).  Each block carries stable id, pageIndex,
 * trimmed text, and sourceKind.
 *
 * When the text has no page markers, returns a single block with
 * pageIndex 0 containing all text.
 *
 * @param {string} sourceText - OCR fulltext or note text.
 * @param {string} sourceKind - One of SOURCE_KINDS values.
 * @returns {Array<{ id: string, pageIndex: number, text: string, sourceKind: string }>}
 */
function buildSourceBlocks(sourceText, sourceKind) {
    if (!sourceText || typeof sourceText !== 'string' || sourceText.trim() === '') {
        return [];
    }

    // Split on page markers, capturing page numbers
    var parts = [];
    var lastIndex = 0;
    var match;
    var pageCounter = 0;

    // Reset regex state
    _PAGE_MARKER_RE.lastIndex = 0;

    while ((match = _PAGE_MARKER_RE.exec(sourceText)) !== null) {
        var markerStart = match.index;
        var markerEnd = match.index + match[0].length;

        // Text before this marker (if any)
        if (markerStart > lastIndex) {
            var beforeText = sourceText.substring(lastIndex, markerStart).trim();
            if (beforeText) {
                parts.push({
                    text: beforeText,
                    pageIndex: pageCounter,
                    markerPage: null, // Not associated with this marker yet
                });
            }
        }

        // Text after the marker (will be associated with this page)
        var pageNum = parseInt(match[1], 10);

        // Find the next marker or end of string
        var nextMarker = _PAGE_MARKER_RE.exec(sourceText);
        var segmentEnd;
        if (nextMarker) {
            segmentEnd = nextMarker.index;
            // Reset so the loop picks up nextMarker on next iteration
            _PAGE_MARKER_RE.lastIndex = nextMarker.index;
        } else {
            segmentEnd = sourceText.length;
        }

        var segmentText = sourceText.substring(markerEnd, segmentEnd).trim();
        if (segmentText) {
            parts.push({
                text: segmentText,
                pageIndex: pageNum,
                markerPage: pageNum,
            });
        } else {
            // No actual content after marker; still push an entry so
            // the page index is represented
            parts.push({
                text: '',
                pageIndex: pageNum,
                markerPage: pageNum,
            });
        }

        lastIndex = segmentEnd;

        if (nextMarker) {
            // We already consumed nextMarker; continue from its position
            continue;
        }
        break;
    }

    // If no markers were found, return single block with all text
    if (parts.length === 0) {
        var trimmed = sourceText.trim();
        if (trimmed) {
            return [{
                id: 'block-0',
                pageIndex: 0,
                text: trimmed,
                sourceKind: sourceKind,
            }];
        }
        return [];
    }

    // Handle any trailing text after the last marker
    if (lastIndex < sourceText.length) {
        var trailing = sourceText.substring(lastIndex).trim();
        if (trailing) {
            parts.push({
                text: trailing,
                pageIndex: parts.length > 0 ? parts[parts.length - 1].pageIndex + 1 : 0,
                markerPage: null,
            });
        }
    }

    // Convert parts to final shape with ids
    var blocks = [];
    for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        if (p.text || p.markerPage != null) {
            blocks.push({
                id: 'block-' + i,
                pageIndex: p.pageIndex,
                text: p.text,
                sourceKind: sourceKind,
            });
        }
    }

    return blocks;
}

/**
 * Offset map entry representing a raw→normalized mapping.
 *
 * @typedef {Object} OffsetEntry
 * @property {number} rawStart - Start index in raw text.
 * @property {number} rawEnd - End index (exclusive) in raw text.
 * @property {number} normStart - Start index in normalized text.
 * @property {number} normEnd - End index (exclusive) in normalized text.
 */

/**
 * Normalize source text for anchor matching.
 *
 * Collapses whitespace runs into single spaces, trims leading/trailing
 * whitespace, and preserves a raw-offset mapping so callers can locate
 * matched substrings back in the original source text.
 *
 * Does NOT change letter case, remove punctuation, or perform any
 * lossy transformation beyond whitespace normalization.
 *
 * @param {string} value - Raw source text to normalize.
 * @returns {{ normalized: string, offsetMap: Array<OffsetEntry> }}
 */
function normalizeSourceTextForAnchors(value) {
    if (typeof value !== 'string' || value.length === 0) {
        return { normalized: '', offsetMap: [] };
    }

    var normalized = '';
    var offsetMap = [];
    var i = 0;
    var len = value.length;

    // Track normalized position as we build
    var normPos = 0;

    // Skip leading whitespace
    while (i < len && _isWhitespace(value[i])) {
        i++;
    }

    while (i < len) {
        var start = i;

        // Collect a non-whitespace segment
        while (i < len && !_isWhitespace(value[i])) {
            i++;
        }

        if (i > start) {
            var segment = value.substring(start, i);
            if (normalized.length > 0) {
                // Add a space before this segment (whitespace collapse)
                offsetMap.push({
                    rawStart: start - 1, // approximate; see below
                    rawEnd: start,
                    normStart: normPos,
                    normEnd: normPos + 1,
                });
                normalized += ' ';
                normPos += 1;
            }

            offsetMap.push({
                rawStart: start,
                rawEnd: i,
                normStart: normPos,
                normEnd: normPos + segment.length,
            });
            normalized += segment;
            normPos += segment.length;
        }

        // Skip whitespace to next word
        var wsStart = i;
        while (i < len && _isWhitespace(value[i])) {
            i++;
        }
        // Note: we don't record individual whitespace spans, only the
        // collapsed space between word segments.
    }

    return { normalized: normalized, offsetMap: offsetMap };
}

/**
 * Check if a character is whitespace (space, tab, newline, carriage return).
 *
 * @param {string} ch - Single character.
 * @returns {boolean}
 * @private
 */
function _isWhitespace(ch) {
    return ch === ' ' || ch === '\t' || ch === '\n' || ch === '\r';
}

module.exports = {
    SOURCE_KINDS: SOURCE_KINDS,
    SOURCE_STATES: SOURCE_STATES,
    buildCanvasSourceModel: buildCanvasSourceModel,
    buildSourceBlocks: buildSourceBlocks,
    normalizeSourceTextForAnchors: normalizeSourceTextForAnchors,
};
