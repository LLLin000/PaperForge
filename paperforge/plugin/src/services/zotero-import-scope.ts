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

export interface LegacyExportFileHint {
  stem: string;
  managedBySqlite: boolean;
}

export interface VeteranZoteroPreselection {
  mode: "preserved" | "matched_legacy" | "unselected";
  selectedKeys: string[];
  matchedNames: string[];
}

const IGNORED_LEGACY_DOMAIN_STEMS = new Set([
  "",
  "unfiled",
  "unfiled_items",
  "literature",
  "literaturecontrol",
  "ai",
  "assets",
]);

/**
 * Inspect existing `exports/*.json` + `Resources/Literature/*` folders to infer
 * the domains a veteran vault already synced before upgrading.
 */
export function collectLegacyDomainNames(args: {
  exportFiles: LegacyExportFileHint[];
  literatureFolders: string[];
}): { legacyDomainNames: string[]; hasManualBbtExports: boolean } {
  const exportFiles = Array.isArray(args.exportFiles) ? args.exportFiles : [];
  const litFolders = Array.isArray(args.literatureFolders)
    ? args.literatureFolders
    : [];

  const hasManualBbtExports = exportFiles.some((f) => !f.managedBySqlite);
  const seen = new Set<string>();
  const legacyDomainNames: string[] = [];
  const pushName = (raw: string) => {
    const cleaned = String(raw || "").trim();
    const norm = cleaned.toLowerCase();
    if (!cleaned || IGNORED_LEGACY_DOMAIN_STEMS.has(norm) || seen.has(norm)) {
      return;
    }
    seen.add(norm);
    legacyDomainNames.push(cleaned);
  };

  for (const f of exportFiles) {
    if (!f.managedBySqlite) pushName(f.stem);
  }
  for (const folder of litFolders) {
    if (!String(folder || "").startsWith(".")) pushName(folder);
  }
  return { legacyDomainNames, hasManualBbtExports };
}

/**
 * Compute safe initial folder checkboxes for a veteran user migrating to Zotero SQLite:
 *  1. Preserve any existing explicit selection (`["*"]` or valid collection keys).
 *  2. Otherwise pre-select only Zotero collections matching existing vault topics/BBT exports.
 *  3. Otherwise leave unselected so the user explicitly chooses a scope before syncing.
 */
export function computeVeteranZoteroPreselection(args: {
  collections: ZoteroCollectionCandidate[];
  existingSelected?: string[];
  legacyDomainNames: string[];
}): VeteranZoteroPreselection {
  const collections = Array.isArray(args.collections) ? args.collections : [];
  const rawExisting = Array.isArray(args.existingSelected)
    ? args.existingSelected.map((s) => String(s || "").trim()).filter(Boolean)
    : [];

  if (rawExisting.includes("*")) {
    return { mode: "preserved", selectedKeys: ["*"], matchedNames: [] };
  }

  const validKeySet = new Set(collections.map((c) => c.key));
  const preservedKeys = Array.from(
    new Set(rawExisting.filter((k) => validKeySet.has(k)))
  );
  if (preservedKeys.length > 0) {
    return { mode: "preserved", selectedKeys: preservedKeys, matchedNames: [] };
  }

  const legacyNorms = new Set(
    (Array.isArray(args.legacyDomainNames) ? args.legacyDomainNames : [])
      .map((s) =>
        String(s || "")
          .trim()
          .toLowerCase()
      )
      .filter((s) => s && !IGNORED_LEGACY_DOMAIN_STEMS.has(s))
  );
  if (legacyNorms.size > 0 && collections.length > 0) {
    const topCols = collections.filter((c) => c.top_level !== false);
    const pool = topCols.length > 0 ? topCols : collections;
    const matched = pool.filter((c) =>
      legacyNorms.has(
        String(c.name || "")
          .trim()
          .toLowerCase()
      )
    );
    const fallbackMatched =
      matched.length > 0
        ? matched
        : collections.filter((c) =>
            legacyNorms.has(
              String(c.name || "")
                .trim()
                .toLowerCase()
            )
          );
    if (fallbackMatched.length > 0) {
      return {
        mode: "matched_legacy",
        selectedKeys: fallbackMatched.map((c) => c.key),
        matchedNames: fallbackMatched.map((c) => c.name),
      };
    }
  }

  return { mode: "unselected", selectedKeys: [], matchedNames: [] };
}
