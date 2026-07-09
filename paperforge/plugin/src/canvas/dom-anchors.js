/**
 * Build an offset index over text that can receive canvas highlights.
 *
 * @param {Node} root
 * @returns {Array<{node: Text, start: number, end: number}>}
 */
function buildTextNodeIndex(root) {
    if (!root || !root.ownerDocument) return [];

    var nodeFilter = root.ownerDocument.defaultView
        && root.ownerDocument.defaultView.NodeFilter;
    var showText = nodeFilter ? nodeFilter.SHOW_TEXT : 4;
    var filterAccept = nodeFilter ? nodeFilter.FILTER_ACCEPT : 1;
    var filterReject = nodeFilter ? nodeFilter.FILTER_REJECT : 2;
    var walker = root.ownerDocument.createTreeWalker(root, showText, {
        acceptNode: function (node) {
            var parent = node.parentElement;
            if (parent && parent.closest(
                'script, style, .paperforge-canvas-highlight'
            )) {
                return filterReject;
            }
            return filterAccept;
        },
    });
    var index = [];
    var offset = 0;
    var node;

    while ((node = walker.nextNode())) {
        var end = offset + node.nodeValue.length;
        index.push({ node: node, start: offset, end: end });
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
    var span = anchor && anchor.sourceSpan ? anchor.sourceSpan : anchor;
    return {
        start: span && span.rawStart,
        end: span && span.rawEnd,
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
 * Apply exact annotation ranges to an already-rendered markdown article.
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
        var overlaps = valid && accepted.some(function (existing) {
            return rangesOverlap(candidate, existing);
        });

        if (!valid || overlaps) {
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
            if (start < end) {
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
