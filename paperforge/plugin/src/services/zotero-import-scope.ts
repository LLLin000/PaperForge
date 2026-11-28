export const LARGE_LIBRARY_FOLDER_GUARD_THRESHOLD = 200;

export interface ZoteroCollectionCandidate {
  key: string;
  name: string;
  item_count?: number;
  top_level?: boolean;
}

export interface ZoteroScopeEvaluation {
  explicitAll: boolean;
  selectedKeys: string[];
  estimatedPapers: number;
  isLargeLibrary: boolean;
  requiresFolderChoice: boolean;
}

/**
 * Evaluate whether a Zotero import scope requires explicit folder selection
 * before importing, so every user with Zotero folders chooses a scope first
 * instead of dumping the entire library directly.
 */
export function evaluateZoteroImportScope(args: {
  totalPapers: number;
  collections: ZoteroCollectionCandidate[];
  selected: string[] | undefined;
}): ZoteroScopeEvaluation {
  const totalPapers = Math.max(0, Number(args.totalPapers || 0));
  const collections = Array.isArray(args.collections) ? args.collections : [];
  const rawSel = Array.isArray(args.selected)
    ? args.selected.map((s) => String(s || "").trim()).filter(Boolean)
    : [];

  const explicitAll = rawSel.includes("*");
  const availableKeys = new Set(collections.map((c) => c.key));
  const selectedKeys = explicitAll
    ? []
    : Array.from(
        new Set(rawSel.filter((k) => k !== "*" && availableKeys.has(k)))
      );

  const topCols = collections.filter((c) => c.top_level !== false);
  const selectableCols = topCols.length > 0 ? topCols : collections;

  const isLargeLibrary = totalPapers > LARGE_LIBRARY_FOLDER_GUARD_THRESHOLD;
  const requiresFolderChoice =
    selectableCols.length > 0 && selectedKeys.length === 0 && !explicitAll;

  let estimatedPapers = totalPapers;
  if (!explicitAll && selectedKeys.length > 0) {
    const pickedSet = new Set(selectedKeys);
    const rawSum = collections
      .filter((c) => pickedSet.has(c.key))
      .reduce((acc, c) => acc + Math.max(0, Number(c.item_count || 0)), 0);
    // An item can belong to multiple selected collections; never show an estimate above totalPapers.
    estimatedPapers = totalPapers > 0 ? Math.min(totalPapers, rawSum) : rawSum;
  }

  return {
    explicitAll,
    selectedKeys,
    estimatedPapers,
    isLargeLibrary,
    requiresFolderChoice,
  };
}
