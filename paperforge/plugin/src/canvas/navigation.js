var NAVIGATION_ACTIONS = {
    SELECT_CARD: 'select-card',
    SELECT_SOURCE: 'select-source',
    SELECT_PAGE_GROUP: 'select-page-group',
    CLEAR_ALL: 'clear-all',
    CLEAR_GROUP: 'clear-group',
    SET_STATUS: 'set-status',
    CLEAR_STATUS: 'clear-status',
    ESCAPE: 'escape',
    REFRESH_PRESERVE: 'refresh-preserve',
    TEARDOWN: 'teardown',
    PAPER_CHANGE: 'paper-change',
};

var SELECTION_STATUSES = {
    SELECTED: 'selected',
    AVAILABLE: 'available',
    UNAVAILABLE: 'unavailable',
    PARTIAL: 'partial',
};

function createInitialNavState() {
    return {
        selectedCardId: null,
        selectedAnchorId: null,
        selectedGroupId: null,
        sourceFocusTargetId: null,
        statusMessage: null,
        navSource: null,
    };
}

function _cloneState(state) {
    return {
        selectedCardId: state.selectedCardId,
        selectedAnchorId: state.selectedAnchorId,
        selectedGroupId: state.selectedGroupId,
        sourceFocusTargetId: state.sourceFocusTargetId,
        statusMessage: state.statusMessage,
        navSource: state.navSource,
    };
}

function reduceCardSelection(state, card, anchors, options) {
    var next = _cloneState(state);
    var opts = options || {};
    if (!card) {
        return next;
    }
    next.selectedCardId = card.cardId || null;
    next.navSource = 'card';
    if (opts.skipScroll) {
        next.sourceFocusTargetId = null;
    } else if (card.anchor && card.anchor.status === 'exact') {
        next.sourceFocusTargetId = card.cardId || null;
    } else if (card.anchor && card.anchor.status === 'page-level') {
        next.sourceFocusTargetId = card.cardId || null;
    } else if (card.anchor && card.anchor.status === 'unresolved') {
        next.sourceFocusTargetId = null;
    } else {
        next.sourceFocusTargetId = null;
        next.statusMessage = 'Unable to locate source anchor for this card.';
    }
    return next;
}

function reduceSourceSelection(state, card, options) {
    var next = _cloneState(state);
    var opts = options || {};
    if (opts.unavailable) {
        next.selectedCardId = null;
        next.selectedAnchorId = null;
        next.selectedGroupId = null;
        next.sourceFocusTargetId = null;
        next.statusMessage = 'Selected card is no longer available.';
        return next;
    }
    if (opts && opts.group) {
        next.selectedGroupId = opts.group.groupId || null;
        next.selectedCardId = null;
        next.navSource = 'source';
        return next;
    }
    if (!card) {
        return next;
    }
    next.selectedAnchorId = card.cardId || null;
    next.selectedCardId = card.cardId || null;
    next.navSource = 'source';
    return next;
}

function reduceLifecycleAction(state, action, options) {
    var opts = options || {};
    if (action === NAVIGATION_ACTIONS.PAPER_CHANGE || action === NAVIGATION_ACTIONS.TEARDOWN) {
        return createInitialNavState();
    }
    if (action === NAVIGATION_ACTIONS.ESCAPE) {
        return createInitialNavState();
    }
    if (action === NAVIGATION_ACTIONS.REFRESH_PRESERVE) {
        var next = _cloneState(state);
        next.sourceFocusTargetId = null;
        next.statusMessage = null;
        next.navSource = null;
        return next;
    }
    if (action === NAVIGATION_ACTIONS.CLEAR_ALL && opts.stale) {
        var next = _cloneState(state);
        next.selectedCardId = null;
        next.selectedAnchorId = null;
        next.selectedGroupId = null;
        next.sourceFocusTargetId = null;
        next.navSource = null;
        next.statusMessage = 'Previous selection is no longer available.';
        return next;
    }
    return _cloneState(state);
}

function computeFallbackEligibility(card, paperKey, resolvedTarget) {
    if (!card) {
        return { eligible: false, reason: 'No card provided.', page: null };
    }
    if (card.pageIndex == null) {
        return { eligible: false, reason: 'Annotation has no page number.', page: null };
    }
    if (!resolvedTarget || !resolvedTarget.ok) {
        return { eligible: false, reason: (resolvedTarget && resolvedTarget.reason) || 'No valid PDF target available.', page: null };
    }
    if (paperKey && card.paperKey && paperKey !== card.paperKey) {
        return { eligible: false, reason: 'Paper identity mismatch.', page: null };
    }
    return { eligible: true, reason: null, page: resolvedTarget.page || card.pageIndex };
}

module.exports = {
    NAVIGATION_ACTIONS: NAVIGATION_ACTIONS,
    SELECTION_STATUSES: SELECTION_STATUSES,
    createInitialNavState: createInitialNavState,
    reduceCardSelection: reduceCardSelection,
    reduceSourceSelection: reduceSourceSelection,
    reduceLifecycleAction: reduceLifecycleAction,
    computeFallbackEligibility: computeFallbackEligibility,
};
