export type Step3BlockResult = { blocked: boolean; reason?: 'ocr' | 'zotero' };

export function shouldBlockStep3(keyValidated: boolean, zoteroDataDir: string): Step3BlockResult {
  if (!zoteroDataDir || !zoteroDataDir.trim()) {
    return { blocked: true, reason: 'zotero' };
  }
  if (!keyValidated) {
    return { blocked: true, reason: 'ocr' };
  }
  return { blocked: false };
}
