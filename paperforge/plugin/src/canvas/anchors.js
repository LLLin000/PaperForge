/**
 * Pure conservative anchor resolver for PaperForge-owned source text
 * (Phase ANN12, Plan 01).
 *
 * Pure CommonJS helpers for resolving card annotations to exact,
 * page-level, or unresolved anchor statuses based on normalized
 * source text matching.  No fs, no Obsidian, no native PDF DOM,
 * no innerHTML, no subprocess.
 *
 * Anchor statuses per D-06 through D-10:
 *   exact      — Normalized selected text has exactly one owned-source match.
 *   page-level — Page metadata available without unique text grounding.
 *   unresolved — No source content or page metadata available.
 *
 * @module canvas/anchors
 */

// ── Anchor constants ──

/**
 * Anchor precision statuses.
 *
 * @enum {string}
 * @readonly
 */
const ANCHOR_STATUSES = Object.freeze({
    EXACT: 'exact',
    PAGE_LEVEL: 'page-level',
    UNRESOLVED: 'unresolved',
});

/**
 * Minimum character length for selected text to qualify for exact anchoring.
 * Text below this threshold always downgrades to page-level or unresolved.
 *
 * @type {number}
 */
const MIN_EXACT_TEXT_CHARS = 3;

// ── Internal normalization helper ──

/**
 * Simple whitespace-collapse normalization for anchor matching.
 *
 * Mirrors the normalization in surface.js but implemented inline so this
 * module has no dependency on surface.js.
 *
 * @param {string} value - Text to normalize.
 * @returns {{ normalized: string, offsetMap: Array<{rawStart: number, rawEnd: number, normStart: number, normEnd: number}> }}
 * @private
 */
function _normalizeText(value) {
    if (typeof value !== 'string' || value.length === 0) {
        return { normalized: '', offsetMap: [] };
    }

    var normalized = '';
    var offsetMap = [];
    var i = 0;
    var len = value.length;
    var normPos = 0;

    // Skip leading whitespace
    while (i < len && _isWs(value[i])) { i++; }

    while (i < len) {
        var start = i;
        while (i < len && !_isWs(value[i])) { i++; }

        if (i > start) {
            var segment = value.substring(start, i);
            if (normalized.length > 0) {
                offsetMap.push({
                    rawStart: start - 1,
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

        while (i < len && _isWs(value[i])) { i++; }
    }

    return { normalized: normalized, offsetMap: offsetMap };
}

/**
 * @param {string} ch - Single character.
 * @returns {boolean}
 * @private
 */
function _isWs(ch) {
    return ch === ' ' || ch === '\t' || ch === '\n' || ch === '\r';
}

/**
 * Map a normalized-text position to raw source offset using the offset map.
 *
 * @param {Array<{rawStart: number, rawEnd: number, normStart: number, normEnd: number}>} offsetMap
 * @param {number} normPos - Position in normalized text.
 * @returns {number|null} Raw position, or null if out of range.
 * @private
 */
function _mapNormToRaw(offsetMap, normPos) {
    if (!Array.isArray(offsetMap)) return null;
    for (var j = 0; j < offsetMap.length; j++) {
        var entry = offsetMap[j];
        if (normPos >= entry.normStart && normPos <= entry.normEnd) {
            // Interpolate within the segment
            var offset = normPos - entry.normStart;
            return entry.rawStart + offset;
        }
    }
    return null;
}

/**
 * Map a normalized-text range to raw source offsets using the offset map.
 *
 * @param {Array<object>} offsetMap
 * @param {number} normStart - Start position in normalized text.
 * @param {number} normEnd - End position in normalized text.
 * @returns {{ rawStart: number|null, rawEnd: number|null }}
 * @private
 */
function _mapNormRangeToRaw(offsetMap, normStart, normEnd) {
    var rawStart = _mapNormToRaw(offsetMap, normStart);
    var rawEnd = _mapNormToRaw(offsetMap, normEnd);

    // If rawEnd is at a segment boundary, use the rawEnd of the segment containing normEnd-1
    if (rawEnd == null && normEnd > normStart) {
        rawEnd = _mapNormToRaw(offsetMap, normEnd - 1);
        if (rawEnd != null) {
            // Add 1 since rawEnd is exclusive
            rawEnd = rawEnd + 1;
        }
    }

    // Fallback: if normEnd equals total normalized length, use last segment's rawEnd
    if (rawEnd == null && offsetMap.length > 0) {
        var last = offsetMap[offsetMap.length - 1];
        rawEnd = last.rawEnd;
    }

    return { rawStart: rawStart, rawEnd: rawEnd };
}

// ── Normalized match finder ──

/**
 * Find all normalized matches of `selectedText` in `sourceText`.
 *
 * Normalizes both texts (whitespace collapse) and locates all occurrences
 * of the normalized selected text in the normalized source text.  Each
 * result maps back to raw source offsets.
 *
 * Returns an empty array when either input is empty, null, or too short.
 *
 * @param {string} sourceText - Raw source text to search in.
 * @param {string} selectedText - Raw selected text to find.
 * @returns {Array<{ normStart: number, normEnd: number, rawStart: number|null, rawEnd: number|null }>}
 */
function findNormalizedSourceMatches(sourceText, selectedText) {
    if (!sourceText || !selectedText || typeof sourceText !== 'string' || typeof selectedText !== 'string') {
        return [];
    }

    if (sourceText.length === 0 || selectedText.length === 0) {
        return [];
    }

    var srcNorm = _normalizeText(sourceText);
    var selNorm = _normalizeText(selectedText);

    var srcText = srcNorm.normalized;
    var selText = selNorm.normalized;

    if (srcText.length === 0 || selText.length === 0) {
        return [];
    }

    var matches = [];
    var searchFrom = 0;

    while (searchFrom <= srcText.length - selText.length) {
        var pos = srcText.indexOf(selText, searchFrom);
        if (pos === -1) break;

        var normStart = pos;
        var normEnd = pos + selText.length;

        var raw = _mapNormRangeToRaw(srcNorm.offsetMap, normStart, normEnd);

        matches.push({
            normStart: normStart,
            normEnd: normEnd,
            rawStart: raw.rawStart,
            rawEnd: raw.rawEnd,
        });

        searchFrom = pos + 1;
    }

    return matches;
}

/**
 * OCR-tolerant normalization with a character-level raw offset map.
 *
 * @param {string} value
 * @returns {{ normalized: string, offsetMap: Array<{rawStart: number, rawEnd: number, normStart: number, normEnd: number}> }}
 */
function normalizeForAnchor(value) {
    if (typeof value !== 'string' || value.length === 0) {
        return { normalized: '', offsetMap: [] };
    }

    var units = [];
    var i = 0;
    while (i < value.length) {
        var rawStart = i;
        var ch = value[i];

        if (/[-\u00ad\u2010\u2011]/.test(ch) && (value[i + 1] === '\n' || value[i + 1] === '\r')) {
            i += 1;
            if (value[i] === '\r' && value[i + 1] === '\n') i += 1;
            i += 1;
            units.push({ text: ' ', rawStart: rawStart, rawEnd: i });
            continue;
        }

        var codePoint = value.codePointAt(i);
        var rawChar = String.fromCodePoint(codePoint);
        i += rawChar.length;
        var normalizedChar = rawChar.normalize('NFKC')
            .replace(/[\u2018\u2019\u201b\u2032]/g, "'")
            .replace(/[\u201c\u201d\u201f\u2033]/g, '"');

        for (var j = 0; j < normalizedChar.length; j++) {
            var out = normalizedChar[j];
            if (/\s/u.test(out) || /[\p{P}\p{S}]/u.test(out)) out = ' ';
            units.push({ text: out, rawStart: rawStart, rawEnd: i });
        }
    }

    var normalized = '';
    var offsetMap = [];
    var pendingSpace = null;
    for (var k = 0; k < units.length; k++) {
        var unit = units[k];
        if (unit.text === ' ') {
            if (normalized.length > 0) {
                if (pendingSpace) {
                    pendingSpace.rawEnd = unit.rawEnd;
                } else {
                    pendingSpace = { rawStart: unit.rawStart, rawEnd: unit.rawEnd };
                }
            }
            continue;
        }
        if (pendingSpace) {
            offsetMap.push({
                rawStart: pendingSpace.rawStart,
                rawEnd: pendingSpace.rawEnd,
                normStart: normalized.length,
                normEnd: normalized.length + 1,
            });
            normalized += ' ';
            pendingSpace = null;
        }
        offsetMap.push({
            rawStart: unit.rawStart,
            rawEnd: unit.rawEnd,
            normStart: normalized.length,
            normEnd: normalized.length + 1,
        });
        normalized += unit.text;
    }

    return { normalized: normalized, offsetMap: offsetMap };
}

function _findOcrNormalizedMatches(sourceText, selectedText) {
    var source = normalizeForAnchor(sourceText);
    var selected = normalizeForAnchor(selectedText);
    if (!source.normalized || !selected.normalized) return [];

    var matches = [];
    var searchFrom = 0;
    while (searchFrom <= source.normalized.length - selected.normalized.length) {
        var pos = source.normalized.indexOf(selected.normalized, searchFrom);
        if (pos === -1) break;
        var end = pos + selected.normalized.length;
        matches.push({
            normStart: pos,
            normEnd: end,
            rawStart: source.offsetMap[pos].rawStart,
            rawEnd: end === source.normalized.length
                ? sourceText.length
                : source.offsetMap[end - 1].rawEnd,
        });
        searchFrom = pos + 1;
    }
    return matches;
}

// ── Anchor resolution ──

/**
 * Resolve anchor status for a single annotation card against a source model.
 *
 * Decision order per D-06 through D-14:
 *   1. Source unavailable → UNRESOLVED
 *   2. Paper identity mismatch → PAGE_LEVEL (with mismatch reason)
 *   3. Selected text empty/missing → PAGE_LEVEL (if page exists) else UNRESOLVED
 *   4. Selected text too short (< MIN_EXACT_TEXT_CHARS) → PAGE_LEVEL (if page exists)
 *   5. Find normalized matches in source text
 *   6. Zero matches → PAGE_LEVEL (if page exists) else UNRESOLVED
 *   7. Exactly one match → EXACT
 *   8. Multiple matches → PAGE_LEVEL (ambiguous)
 *
 * @param {object} card - Annotation card ({ cardId, selectedText, pageIndex, pageLabel?, paperKey? }).
 * @param {object} sourceModel - Source model from buildCanvasSourceModel().
 * @param {object} [options] - Optional flags (reserved for future use).
 * @returns {{ anchorId: string, cardId: string, status: string, sourceKind: string|null,
 *            reason: string|null, matchCount: number, pageIndex: number|null,
 *            sourceSpan: object|null, diagnostics: object }}
 */
function _resolveCanvasAnchorLegacy(card, sourceModel, options) {
    var cardId = (card && card.cardId) || '';
    var selectedText = (card && card.selectedText) || '';
    var pageIndex = (card && card.pageIndex) != null ? card.pageIndex : null;
    var cardPaperKey = (card && card.paperKey) || null;

    var anchorId = 'anchor-' + (cardId || 'unknown');

    // ── Guard: missing card ──
    if (!card || !cardId) {
        return {
            anchorId: anchorId,
            cardId: cardId || '',
            status: ANCHOR_STATUSES.UNRESOLVED,
            sourceKind: null,
            reason: 'Card has no identity.',
            matchCount: 0,
            pageIndex: pageIndex,
            sourceSpan: null,
            diagnostics: { cardMissing: true },
        };
    }

    // ── Step 1: Source unavailable → UNRESOLVED ──
    var sourceStatus = (sourceModel && sourceModel.status) || 'source-unavailable';
    var sourceKind = (sourceModel && sourceModel.sourceKind) || null;
    var sourceText = (sourceModel && sourceModel.text) || null;
    var modelPaperKey = (sourceModel && sourceModel.diagnostics && sourceModel.diagnostics.fulltext) ? null : null;

    if (sourceStatus === 'source-unavailable' || sourceKind == null) {
        var reason = (sourceModel && sourceModel.reason) || 'Source content is not available.';
        return {
            anchorId: anchorId,
            cardId: cardId,
            status: ANCHOR_STATUSES.UNRESOLVED,
            sourceKind: sourceKind,
            reason: reason,
            matchCount: 0,
            pageIndex: pageIndex,
            sourceSpan: null,
            diagnostics: {
                sourceUnavailable: true,
                sourceReason: reason,
            },
        };
    }

    // ── Step 2: Paper identity mismatch? ──
    // Source model carries the entry paper key from surface.js.
    var sourcePaperKey = (sourceModel && sourceModel.paperKey) || null;

    if (cardPaperKey && sourcePaperKey && cardPaperKey !== sourcePaperKey) {
        return {
            anchorId: anchorId,
            cardId: cardId,
            status: ANCHOR_STATUSES.PAGE_LEVEL,
            sourceKind: sourceKind,
            reason: 'Source text belongs to a different paper. (source-identity-mismatch)',
            matchCount: 0,
            pageIndex: pageIndex,
            sourceSpan: null,
            diagnostics: {
                cardPaperKey: cardPaperKey,
                sourcePaperKey: sourcePaperKey,
                identityMismatch: true,
            },
        };
    }

    // ── Step 3: Empty/selected text ──
    var hasPageMetadata = pageIndex != null && pageIndex >= 0;

    if (!selectedText || selectedText.trim().length === 0) {
        if (hasPageMetadata) {
            return {
                anchorId: anchorId,
                cardId: cardId,
                status: ANCHOR_STATUSES.PAGE_LEVEL,
                sourceKind: sourceKind,
                reason: 'No selected text. Using page-level anchor.',
                matchCount: 0,
                pageIndex: pageIndex,
                sourceSpan: null,
                diagnostics: { emptySelectedText: true },
            };
        }
        return {
            anchorId: anchorId,
            cardId: cardId,
            status: ANCHOR_STATUSES.UNRESOLVED,
            sourceKind: sourceKind,
            reason: 'No selected text and no page metadata.',
            matchCount: 0,
            pageIndex: pageIndex,
            sourceSpan: null,
            diagnostics: { emptySelectedText: true, noPageMetadata: true },
        };
    }

    // ── Step 4: Text too short? ──
    // Use trimmed length for MIN_EXACT_TEXT_CHARS threshold check
    var trimLen = selectedText.trim().length;

    if (trimLen < MIN_EXACT_TEXT_CHARS) {
        return {
            anchorId: anchorId,
            cardId: cardId,
            status: ANCHOR_STATUSES.PAGE_LEVEL,
            sourceKind: sourceKind,
            reason: 'Selected text is too short for exact anchoring. (' + trimLen + ' chars)',
            matchCount: 0,
            pageIndex: pageIndex,
            sourceSpan: null,
            diagnostics: { textTooShort: true, textLength: trimLen, minChars: MIN_EXACT_TEXT_CHARS },
        };
    }

    // ── Step 5: Find normalized matches ──
    // If there's no source text, downgrade
    if (!sourceText || sourceText.length === 0) {
        if (hasPageMetadata) {
            return {
                anchorId: anchorId,
                cardId: cardId,
                status: ANCHOR_STATUSES.PAGE_LEVEL,
                sourceKind: sourceKind,
                reason: 'Source text is empty. Using page-level anchor.',
                matchCount: 0,
                pageIndex: pageIndex,
                sourceSpan: null,
                diagnostics: { emptySourceText: true },
            };
        }
        return {
            anchorId: anchorId,
            cardId: cardId,
            status: ANCHOR_STATUSES.UNRESOLVED,
            sourceKind: sourceKind,
            reason: 'Source text is empty.',
            matchCount: 0,
            pageIndex: pageIndex,
            sourceSpan: null,
            diagnostics: { emptySourceText: true },
        };
    }

    var matches = findNormalizedSourceMatches(sourceText, selectedText);
    var matchCount = matches.length;

    // ── Step 6: Zero matches ──
    if (matchCount === 0) {
        if (hasPageMetadata) {
            return {
                anchorId: anchorId,
                cardId: cardId,
                status: ANCHOR_STATUSES.PAGE_LEVEL,
                sourceKind: sourceKind,
                reason: 'Selected text not found in source. Using page-level anchor.',
                matchCount: 0,
                pageIndex: pageIndex,
                sourceSpan: null,
                diagnostics: { textNotFoundInSource: true },
            };
        }
        return {
            anchorId: anchorId,
            cardId: cardId,
            status: ANCHOR_STATUSES.UNRESOLVED,
            sourceKind: sourceKind,
            reason: 'Selected text not found in source.',
            matchCount: 0,
            pageIndex: pageIndex,
            sourceSpan: null,
            diagnostics: { textNotFoundInSource: true },
        };
    }

    // ── Step 7: Exactly one match → EXACT ──
    if (matchCount === 1) {
        var match = matches[0];
        return {
            anchorId: anchorId,
            cardId: cardId,
            status: ANCHOR_STATUSES.EXACT,
            sourceKind: sourceKind,
            reason: null,
            matchCount: 1,
            pageIndex: pageIndex,
            sourceSpan: {
                rawStart: match.rawStart,
                rawEnd: match.rawEnd,
                normStart: match.normStart,
                normEnd: match.normEnd,
            },
            diagnostics: {
                exactMatch: true,
                normalizedMatch: selectedText,
            },
        };
    }

    // ── Step 8: Multiple matches → PAGE_LEVEL (ambiguous) ──
    return {
        anchorId: anchorId,
        cardId: cardId,
        status: ANCHOR_STATUSES.PAGE_LEVEL,
        sourceKind: sourceKind,
        reason: 'Selected text appears ' + matchCount + ' times in source (ambiguous).',
        matchCount: matchCount,
        pageIndex: pageIndex,
        sourceSpan: null,
        diagnostics: { ambiguousMatch: true, matchCount: matchCount },
    };
}

function _withMatchingMetadata(anchor, strategy, confidence, candidateCount, match) {
    var result = Object.assign({}, anchor, {
        strategy: strategy,
        confidence: confidence,
        candidateCount: candidateCount,
        rawStart: match ? match.rawStart : null,
        rawEnd: match ? match.rawEnd : null,
    });
    result.matchCount = candidateCount;
    return result;
}

/**
 * Resolve an anchor in conservative literal, OCR-normalized, then page-context stages.
 */
function resolveCanvasAnchor(card, sourceModel, options) {
    var legacy = _resolveCanvasAnchorLegacy(card, sourceModel, options);
    var selectedText = card && typeof card.selectedText === 'string' ? card.selectedText : '';
    var sourceText = sourceModel && typeof sourceModel.text === 'string' ? sourceModel.text : '';
    var canMatch = card && card.cardId && selectedText.trim().length >= MIN_EXACT_TEXT_CHARS &&
        sourceText.length > 0 && !legacy.diagnostics.identityMismatch;

    if (!canMatch) {
        var fallbackStrategy = legacy.status === ANCHOR_STATUSES.PAGE_LEVEL ? 'page-context' : 'none';
        return _withMatchingMetadata(
            legacy,
            fallbackStrategy,
            legacy.status === ANCHOR_STATUSES.PAGE_LEVEL ? 0.5 : 0,
            legacy.matchCount || 0,
            null
        );
    }

    var literalMatches = findNormalizedSourceMatches(sourceText, selectedText);
    if (literalMatches.length === 1) {
        var literal = literalMatches[0];
        return _withMatchingMetadata(_resolveCanvasAnchorLegacy(card, sourceModel, options), 'literal', 1, 1, literal);
    }
    if (literalMatches.length > 1) {
        return _withMatchingMetadata(Object.assign({}, legacy, {
            status: ANCHOR_STATUSES.UNRESOLVED,
            reason: 'Selected text has ambiguous literal matches in source.',
            sourceSpan: null,
            diagnostics: { ambiguousMatch: true, matchCount: literalMatches.length },
        }), 'none', 0, literalMatches.length, null);
    }

    var ocrMatches = _findOcrNormalizedMatches(sourceText, selectedText);
    if (ocrMatches.length === 1) {
        var ocr = ocrMatches[0];
        return _withMatchingMetadata(Object.assign({}, legacy, {
            status: ANCHOR_STATUSES.EXACT,
            reason: null,
            sourceSpan: {
                rawStart: ocr.rawStart,
                rawEnd: ocr.rawEnd,
                normStart: ocr.normStart,
                normEnd: ocr.normEnd,
            },
            diagnostics: { exactMatch: true, ocrNormalizedMatch: true },
        }), 'ocr-normalized', 0.95, 1, ocr);
    }
    if (ocrMatches.length > 1) {
        return _withMatchingMetadata(Object.assign({}, legacy, {
            status: ANCHOR_STATUSES.UNRESOLVED,
            reason: 'Selected text has ambiguous OCR-normalized matches in source.',
            sourceSpan: null,
            diagnostics: { ambiguousMatch: true, matchCount: ocrMatches.length },
        }), 'none', 0, ocrMatches.length, null);
    }

    var strategy = legacy.status === ANCHOR_STATUSES.PAGE_LEVEL ? 'page-context' : 'none';
    return _withMatchingMetadata(
        legacy,
        strategy,
        legacy.status === ANCHOR_STATUSES.PAGE_LEVEL ? 0.5 : 0,
        0,
        null
    );
}

/**
 * Resolve anchors for multiple cards in batch.
 *
 * @param {Array<object>} cards - Array of card objects.
 * @param {object} sourceModel - Source model from buildCanvasSourceModel().
 * @param {object} [options] - Optional flags (reserved).
 * @returns {Array<object>} Array of anchor results.
 */
function resolveCanvasAnchors(cards, sourceModel, options) {
    if (!Array.isArray(cards)) return [];
    return cards.map(function (card) {
        return resolveCanvasAnchor(card, sourceModel, options);
    });
}

module.exports = {
    ANCHOR_STATUSES: ANCHOR_STATUSES,
    MIN_EXACT_TEXT_CHARS: MIN_EXACT_TEXT_CHARS,
    resolveCanvasAnchor: resolveCanvasAnchor,
    resolveCanvasAnchors: resolveCanvasAnchors,
    findNormalizedSourceMatches: findNormalizedSourceMatches,
    normalizeForAnchor: normalizeForAnchor,
};
