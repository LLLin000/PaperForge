import * as path from 'path';

export function extractZoteroKeyFromPath(filePath: string): string | null {
  if (!filePath) return null;
  let dir = path.dirname(filePath);
  while (true) {
    const basename = path.basename(dir);
    if (!basename || basename === '.') break;
    const match = basename.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (match) return match[1];
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}
