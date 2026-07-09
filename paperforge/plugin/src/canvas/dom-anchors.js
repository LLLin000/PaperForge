/**
 * Build rendered article text offsets over every text node.
 *
 * Offsets match the complete rendered article textContent, not the source
 * Markdown. Text inside mark, script, or style elements remains in the index
 * with blocked=true so later node offsets are not compressed.
 *
 * @param {Node} root
 * @returns {Array<{node: Text, start: number, end: number, blocked: boolean}>}
 */
function buildTextNodeIndex(root) {
    if (!root || !root.ownerDocument) return [];

    var nodeFilter = root.ownerDocument.defaultView
        && root.ownerDocument.defaultView.NodeFilter;
    var showText = nodeFilter ? nodeFilter.SHOW_TEXT : 4;
    var walker = root.ownerDocument.createTreeWalker(root, showText);
    var index = [];
    var offset = 0;
    var node;

    while ((node = walker.nextNode())) {
        var end = offset + node.nodeValue.length;
        var parent = node.parentElement;
        index.push({
            node: node,
            start: offset,
            end: end,
            blocked: Boolean(parent && parent.closest('script, style, mark')),
        });
        offset = end;
    }

    return index;
}

function getAnchorId(anchor) {
    if (!anchor) return '';
    var id = anchor.id != null
        ? anchor.id
        : (anchor.anchorId != null ? anchor.anchorId : anchor.cardId);
    return id == null ? '' : String(id);
}

function getAnchorRange(anchor) {
    return {
        start: anchor && anchor.renderedStart,
        end: anchor && anchor.renderedEnd,
    };
}

function rangesOverlap(left, right) {
    return left.start < right.end && right.start < left.end;
}

function wrapTextSegment(entry, start, end, anchor) {
    var node = entry.node;
    var localStart = start - entry.start;
    var localEnd = end - entry.start;

    if (localEnd < node.nodeValue.length) {
        node.splitText(localEnd);
    }
    var selected = localStart > 0 ? node.splitText(localStart) : node;
    var mark = selected.ownerDocument.createElement('mark');
    mark.className = 'paperforge-canvas-highlight';
    mark.setAttribute('data-anchor-id', anchor.id);
    mark.setAttribute('data-anchor-status', 'exact');
    mark.setAttribute('tabindex', '0');
    if (anchor.color) {
        mark.style.setProperty('--paperforge-highlight-color', anchor.color);
    }
    selected.parentNode.replaceChild(mark, selected);
    mark.appendChild(selected);
}

/**
 * Apply exact annotation ranges to an already-rendered Markdown article.
 *
 * Anchors must provide renderedStart/renderedEnd offsets measured against the
 * complete rendered article textContent indexed by buildTextNodeIndex().
 * Source Markdown rawStart/rawEnd coordinates are intentionally not accepted.
 * Ranges intersecting blocked mark, script, or style text are unresolved.
 *
 * @param {Node} article
 * @param {Array<object>} anchors
 * @returns {{applied: string[], unresolved: string[]}}
 */
function applyDomHighlights(article, anchors) {
    var index = buildTextNodeIndex(article);
    var textLength = index.length ? index[index.length - 1].end : 0;
    var accepted = [];
    var applied = [];
    var unresolved = [];
    var seenIds = new Set();

    (Array.isArray(anchors) ? anchors : []).forEach(function (anchor) {
        var id = getAnchorId(anchor);
        var range = getAnchorRange(anchor);
        var candidate = {
            id: id,
            start: range.start,
            end: range.end,
            color: anchor && (anchor.color || anchor.highlightColor),
        };
        var valid = id
            && Number.isInteger(candidate.start)
            && Number.isInteger(candidate.end)
            && candidate.start >= 0
            && candidate.end > candidate.start
            && candidate.end <= textLength;
        var duplicate = id && seenIds.has(id);
        var overlaps = valid && accepted.some(function (existing) {
            return rangesOverlap(candidate, existing);
        });
        var intersectsBlocked = valid && index.some(function (entry) {
            return entry.blocked && rangesOverlap(candidate, entry);
        });

        if (id) seenIds.add(id);
        if (!valid || duplicate || overlaps || intersectsBlocked) {
            unresolved.push(id);
            return;
        }
        accepted.push(candidate);
        applied.push(id);
    });

    accepted.slice().sort(function (left, right) {
        return right.start - left.start || right.end - left.end;
    }).forEach(function (anchor) {
        for (var i = index.length - 1; i >= 0; i -= 1) {
            var entry = index[i];
            var start = Math.max(anchor.start, entry.start);
            var end = Math.min(anchor.end, entry.end);
            if (!entry.blocked && start < end) {
                wrapTextSegment(entry, start, end, anchor);
            }
        }
    });

    return { applied: applied, unresolved: unresolved };
}

module.exports = {
    applyDomHighlights,
    buildTextNodeIndex,
};
