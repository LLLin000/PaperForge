/**
 * version-diff — PURE text diff for display-fulltext versions.
 *
 * Ticket 07 step 6 item 6 boundary: version discovery, manifest
 * interpretation, path construction, restore and provenance are Python
 * authority. What stays host-side is exactly this: given two texts the
 * user is looking at, show what changed. No filesystem, no manifest, no
 * identity derivation.
 */

export interface DiffResult {
  paragraphIndex: number;
  heading: string;
  type: "unchanged" | "added" | "removed" | "changed";
  oldText?: string;
  newText?: string;
}

/** Paragraph-level diff between two version fulltext texts. */
export function diffFulltext(textA: string, textB: string): DiffResult[] {
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

/** Flat added/removed line view (workspace modal). */
export function diffParagraphs(
  textA: string,
  textB: string
): { type: "added" | "removed" | "unchanged"; text: string }[] {
  const split = (t: string) => t.split(/\n\n+/).filter(Boolean);
  const pa = split(textA);
  const pb = split(textB);
  const max = Math.max(pa.length, pb.length);
  const result: { type: "added" | "removed" | "unchanged"; text: string }[] =
    [];
  for (let i = 0; i < max; i++) {
    const a = i < pa.length ? pa[i] : "";
    const b = i < pb.length ? pb[i] : "";
    if (!a && b) result.push({ type: "added", text: b });
    else if (a && !b) result.push({ type: "removed", text: a });
    else if (a !== b) {
      result.push({ type: "removed", text: a });
      result.push({ type: "added", text: b });
    } else {
      result.push({ type: "unchanged", text: a });
    }
  }
  return result;
}

function splitParagraphs(text: string): string[] {
  const lines = text.split("\n");
  const blocks: string[] = [];
  let current: string[] = [];

  for (const line of lines) {
    if (line.startsWith("## ") && current.length > 0) {
      blocks.push(current.join("\n").trim());
      current = [line];
    } else if (line.trim() === "" && current.length > 0) {
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
