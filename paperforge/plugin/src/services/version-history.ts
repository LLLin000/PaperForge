import * as fs from "fs";
import * as path from "path";
import { resolveVaultPaths } from "./memory-state";

// ── Types ──

export interface VersionEntry {
  label: string;
  created_at: string;
  source: string;
  renderer_version?: string;
  structured_content_hash?: string;
  fulltext_size: number;
}

export interface PaperVersionInfo {
  key: string;
  title: string;
  versions: VersionEntry[];
  currentLabel: string;
  totalSize: number;
}

export interface DiffResult {
  paragraphIndex: number;
  heading: string;
  type: "unchanged" | "added" | "removed" | "changed";
  oldText?: string;
  newText?: string;
}

// ── Helpers ──

function ocrRoot(vaultPath: string): string {
  const paths = resolveVaultPaths(vaultPath);
  return paths.ocrDir;
}

/** Read and parse manifest.json for a paper key. Returns null on any failure. */
function readManifest(
  vaultPath: string,
  paperKey: string
): { versions: VersionEntry[]; current: { label: string } } | null {
  const manifestPath = path.join(
    ocrRoot(vaultPath),
    paperKey,
    "versions",
    "manifest.json"
  );
  try {
    if (!fs.existsSync(manifestPath)) return null;
    const raw = fs.readFileSync(manifestPath, "utf-8");
    const parsed: unknown = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed === "object" &&
      "versions" in parsed &&
      "current" in parsed
    ) {
      const obj = parsed as Record<string, unknown>;
      const versions = obj["versions"];
      const current = obj["current"];
      if (
        Array.isArray(versions) &&
        current &&
        typeof current === "object" &&
        "label" in current
      ) {
        return parsed as {
          versions: VersionEntry[];
          current: { label: string };
        };
      }
    }
    return null;
  } catch {
    return null;
  }
}

/** List all directories under the OCR root (each is a paper key). */
function listOcrPaperDirs(vaultPath: string): string[] {
  const root = ocrRoot(vaultPath);
  try {
    if (!fs.existsSync(root)) return [];
    return fs
      .readdirSync(root, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => d.name);
  } catch {
    return [];
  }
}

// ── Exported API ──

/**
 * Read version manifest for a single paper key.
 * Returns the version list plus the current label, or null.
 */
export function scanVersions(
  vaultPath: string,
  paperKey: string
): { versions: VersionEntry[]; currentLabel: string } | null {
  const manifest = readManifest(vaultPath, paperKey);
  if (!manifest) return null;
  return {
    versions: manifest.versions,
    currentLabel: manifest.current.label,
  };
}

/**
 * Scan all OCR paper directories for version manifests.
 * Returns an array of PaperVersionInfo, one per paper that has backups.
 */
export function listPapersWithBackups(vaultPath: string): PaperVersionInfo[] {
  const dirs = listOcrPaperDirs(vaultPath);
  const results: PaperVersionInfo[] = [];

  for (const key of dirs) {
    const manifest = readManifest(vaultPath, key);
    if (!manifest) continue;
    const labels = manifest.versions.map((v) => v.label);

    // Inline size estimate
    let totalSize = 0;
    for (const label of labels) {
      const ftPath = path.join(
        ocrRoot(vaultPath),
        key,
        "versions",
        label,
        "fulltext.md"
      );
      try {
        if (fs.existsSync(ftPath)) {
          totalSize += fs.statSync(ftPath).size;
        }
      } catch {
        // skip
      }
    }

    results.push({
      key,
      title: key.replace(/_/g, " "),
      versions: manifest.versions,
      currentLabel: manifest.current.label,
      totalSize,
    });
  }

  results.sort((a, b) => a.title.localeCompare(b.title));
  return results;
}

/**
 * Restore a specific version's fulltext.md to the render/ directory.
 * Returns true on success, false on failure.
 */
export function restoreVersion(
  vaultPath: string,
  paperKey: string,
  label: string
): boolean {
  const root = ocrRoot(vaultPath);
  const sourcePath = path.join(
    root,
    paperKey,
    "versions",
    label,
    "fulltext.md"
  );
  const targetDir = path.join(root, paperKey, "render");
  const targetPath = path.join(targetDir, "fulltext.md");

  try {
    if (!fs.existsSync(sourcePath)) return false;
    if (!fs.existsSync(targetDir)) {
      fs.mkdirSync(targetDir, { recursive: true });
    }
    fs.copyFileSync(sourcePath, targetPath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Paragraph-level diff between two version fulltext files.
 * Paragraphs are split by double-newline or `## `-prefixed headings.
 * Returns a list of changed paragraphs.
 */
export function compareVersions(
  vaultPath: string,
  paperKey: string,
  labelA: string,
  labelB: string
): DiffResult[] {
  const root = ocrRoot(vaultPath);
  const pathA = path.join(root, paperKey, "versions", labelA, "fulltext.md");
  const pathB = path.join(root, paperKey, "versions", labelB, "fulltext.md");

  let textA = "";
  let textB = "";
  try {
    if (fs.existsSync(pathA)) textA = fs.readFileSync(pathA, "utf-8");
  } catch {
    /* empty */
  }
  try {
    if (fs.existsSync(pathB)) textB = fs.readFileSync(pathB, "utf-8");
  } catch {
    /* empty */
  }

  const paragraphsA = splitParagraphs(textA);
  const paragraphsB = splitParagraphs(textB);

  const maxLen = Math.max(paragraphsA.length, paragraphsB.length);
  const results: DiffResult[] = [];

  for (let i = 0; i < maxLen; i++) {
    const oldText = i < paragraphsA.length ? paragraphsA[i] : "";
    const newText = i < paragraphsB.length ? paragraphsB[i] : "";
    const firstHdrLine = (oldText || newText).split("\n")[0] ?? "";
    const heading = firstHdrLine.startsWith("## ")
      ? firstHdrLine.replace(/^##\s+/, "")
      : "";

    let type: DiffResult["type"] = "unchanged";
    if (!oldText && newText) {
      type = "added";
    } else if (oldText && !newText) {
      type = "removed";
    } else if (oldText !== newText) {
      type = "changed";
    }

    if (type !== "unchanged") {
      results.push({
        paragraphIndex: i,
        heading,
        type,
        oldText: oldText || undefined,
        newText: newText || undefined,
      });
    }
  }

  return results;
}

// ── Internal diff helpers ──

function splitParagraphs(text: string): string[] {
  // Split by `## `-prefixed headings or double-newline blocks
  const lines = text.split("\n");
  const blocks: string[] = [];
  let current: string[] = [];

  for (const line of lines) {
    if (line.startsWith("## ") && current.length > 0) {
      blocks.push(current.join("\n").trim());
      current = [line];
    } else if (line.trim() === "" && current.length > 0) {
      // Double-newline boundary: commit if the last committed is not empty
      const joined = current.join("\n").trim();
      if (joined) {
        blocks.push(joined);
        current = [];
      }
    } else {
      current.push(line);
    }
  }

  if (current.length > 0) {
    const joined = current.join("\n").trim();
    if (joined) blocks.push(joined);
  }

  return blocks;
}
