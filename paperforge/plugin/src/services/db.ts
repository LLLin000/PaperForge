import * as fs from "fs";
import * as path from "path";
import initSqlJs from "sql.js";
import type {
  Database as SqlJsDatabase,
  Statement as SqlJsStatement,
  SqlValue,
} from "sql.js";

// ── Types ──

export interface SearchResultItem {
  zotero_key: string;
  title: string;
  first_author: string;
  year: string;
  journal: string;
  domain: string;
  abstract: string;
  rank: number;
}

// ── Module-level state (lazy init) ──

let _db: SqlJsDatabase | null = null;
let _queryStmt: SqlJsStatement | null = null;

// ── FTS5 query transform ──
// FTS5 requires explicit operators between terms: "rotator cuff" → "rotator AND cuff"
// Quoted phrases like '"rotator cuff"' are passed through verbatim.

function transformFtsQuery(input: string): string {
  input = input.trim();
  if (!input) return "";

  // Already a quoted phrase — pass through as-is
  if (input.startsWith('"') && input.endsWith('"')) {
    return input;
  }

  const terms = input.split(/\s+/).filter(Boolean);
  if (terms.length === 0) return "";
  return terms.join(" AND ");
}

// ── Database init (lazy) ──

function sqlValueToString(v: SqlValue): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v;
  if (v instanceof Uint8Array) return new TextDecoder().decode(v);
  return String(v);
}

function sqlValueToNumber(v: SqlValue): number {
  if (v === null || v === undefined) return 0;
  if (typeof v === "number") return v;
  return Number(v);
}

export async function initDatabase(vaultPath: string): Promise<void> {
  const dbPath = path.join(
    vaultPath,
    "System",
    "PaperForge",
    "indexes",
    "paperforge.db"
  );

  if (!fs.existsSync(dbPath)) {
    throw new Error(`PaperForge database not found at ${dbPath}`);
  }

  const SQL = await initSqlJs({
    locateFile: (file: string) => path.join(__dirname, file),
  });

  const buffer = fs.readFileSync(dbPath);
  _db = new SQL.Database(new Uint8Array(buffer));

  _queryStmt = _db.prepare(
    `SELECT zotero_key, title, first_author, year, journal, domain, abstract, rank
     FROM paper_fts
     WHERE paper_fts MATCH ?
     ORDER BY rank
     LIMIT ?`
  );
}

// ── Search ──

export function searchMetadata(
  query: string,
  limit: number = 20
): SearchResultItem[] | null {
  if (!_db || !_queryStmt) return null;

  const transformed = transformFtsQuery(query);
  if (!transformed) return [];

  _queryStmt.bind([transformed, limit]);

  const results: SearchResultItem[] = [];
  while (_queryStmt.step()) {
    const row = _queryStmt.getAsObject();
    results.push({
      zotero_key: sqlValueToString(row.zotero_key),
      title: sqlValueToString(row.title),
      first_author: sqlValueToString(row.first_author),
      year: sqlValueToString(row.year),
      journal: sqlValueToString(row.journal),
      domain: sqlValueToString(row.domain),
      abstract: sqlValueToString(row.abstract),
      rank: sqlValueToNumber(row.rank),
    });
  }
  _queryStmt.reset();
  return results;
}
