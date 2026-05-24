# Plugin Overlay Adapter Design

> Obsidian plugin side of the annotation overlay system.

## Module Structure

```
plugin/src/
├── main.ts                       ← extended: add annotation commands
├── pdf-overlay/
│   ├── patch-pdf-viewer.ts       ← monkey-around patches
│   ├── overlay-layer.ts          ← overlay DOM management
│   ├── rect-renderer.ts          ← rect placement + colors
│   ├── selection-handler.ts      ← text selection → annotation
│   ├── popover.ts                ← annotation popover
│   ├── annotation-fetcher.ts     ← execFile bridge
│   └── types.ts                  ← interfaces
└── testable.js                   ← extended
```

## Patch Sequence (in `patch-pdf-viewer.ts`)

```typescript
import { around } from 'monkey-around';
import { Plugin } from 'obsidian';

export function patchPDFViewer(plugin: Plugin): boolean {
    // Step 1: Get PDFView constructor
    const pdfLeaves = plugin.app.workspace.getLeavesOfType('pdf');
    if (!pdfLeaves.length) return false;
    const pdfView = pdfLeaves[0].view as any;
    const PDFViewerChildProto = pdfView.constructor.prototype;

    // Step 2: Patch loadFile to inject annotation overlay
    plugin.register(around(PDFViewerChildProto, {
        loadFile(old: Function) {
            return function (this: any, file: any) {
                const result = old.call(this, file);
                initOverlayForFile(this, file);
                return result;
            };
        }
    }));

    // Step 3: Patch load to register event listeners
    plugin.register(around(PDFViewerChildProto, {
        load(old: Function) {
            return function (this: any) {
                const result = old.call(this);
                registerOverlayEvents(this);
                return result;
            };
        },
        unload(old: Function) {
            return function (this: any) {
                cleanupOverlay(this);
                return old.call(this);
            };
        }
    }));

    return true;
}
```

## Overlay Layer Management (in `overlay-layer.ts`)

```typescript
export class OverlayLayerManager {
    private pageLayers: Map<number, HTMLElement> = new Map();

    getOrCreateLayer(pageView: any): HTMLElement {
        const pageDiv = pageView.div;
        let layer = pageDiv.querySelector('div.pf-annotation-overlay') as HTMLElement;
        if (!layer) {
            layer = pageDiv.createDiv('pf-annotation-overlay');
            window.pdfjsLib.setLayerDimensions(layer, pageView.viewport);
        }
        return layer;
    }

    clearPage(pageNumber: number): void {
        const layer = this.pageLayers.get(pageNumber);
        if (layer) layer.empty();
    }

    clearAll(): void {
        this.pageLayers.forEach(layer => layer.empty());
        this.pageLayers.clear();
    }
}
```

## Rect Renderer (in `rect-renderer.ts`)

```typescript
export interface AnnotationRect {
    id: string;
    type: 'highlight' | 'underline' | 'note';
    rect: [number, number, number, number]; // PDF coords [left, bottom, right, top]
    color: string;
    comment?: string;
    isReadonly: boolean;
}

export class RectRenderer {
    render(rects: AnnotationRect[], pageView: any, layer: HTMLElement): void {
        const viewport = pageView.viewport;
        const [pageX, pageY, pageX2, pageY2] = viewport.viewBox;
        const pageW = pageX2 - pageX;
        const pageH = pageY2 - pageY;

        for (const ann of rects) {
            const [left, bottom, right, top] = ann.rect;
            const mirrored = window.pdfjsLib.Util.normalizeRect([
                left, pageY2 - bottom + pageY,
                right, pageY2 - top + pageY
            ]);

            const el = layer.createDiv('pf-annotation-rect');
            el.dataset.annotationId = ann.id;
            el.dataset.type = ann.type;

            el.setCssStyles({
                left: `${100 * (mirrored[0] - pageX) / pageW}%`,
                top: `${100 * (mirrored[1] - pageY) / pageH}%`,
                width: `${100 * (mirrored[2] - mirrored[0]) / pageW}%`,
                height: `${100 * (mirrored[3] - mirrored[1]) / pageH}%`,
            });

            if (ann.type === 'highlight') {
                el.style.background = hexToRgba(ann.color, 0.25);
            } else if (ann.type === 'underline') {
                el.style.borderBottom = `2px solid ${ann.color}`;
            } else if (ann.type === 'note') {
                el.style.background = hexToRgba(ann.color, 0.15);
                el.style.border = `1px solid ${ann.color}`;
            }

            if (ann.isReadonly) {
                el.classList.add('pf-annotation-readonly');
            }
        }
    }
}

function hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
```

## Selection Handler (in `selection-handler.ts`)

```typescript
export class SelectionHandler {
    private pendingButton: HTMLElement | null = null;

    handleSelection(pageView: any): void {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) {
            this.removePendingButton();
            return;
        }

        const range = selection.getRangeAt(0);
        const textLayer = pageView.textLayer;
        if (!textLayer) return;

        // Determine page index and selected rects
        const pageNumber = pageView.id;
        const selectedText = selection.toString().trim();
        if (!selectedText) return;

        // Show floating "Add Highlight" button
        this.showAddButton(pageView, range, selectedText);
    }

    private async addAnnotation(pageView: any, selectedText: string, rects: number[][]): Promise<void> {
        const sortIndex = this.buildSortIndex(pageView.id, 0, 0);
        const position = {
            pageIndex: pageView.id - 1,
            rects: rects.map(r => [r[0], r[1], r[2], r[3]]),
        };

        // execFile → paperforge annotation create
        const result = await createAnnotation({
            paperKey: currentPaperKey,
            type: 'highlight',
            pageIndex: pageView.id - 1,
            selectedText,
            color: '#ffd400',
            position,
            sortIndex,
        });

        // Optimistic add to overlay
        renderSingleAnnotation(result, pageView);
    }
}
```

## Popover (in `popover.ts`)

```typescript
export class AnnotationPopover {
    private popoverEl: HTMLElement | null = null;

    show(annotation: Annotation, rect: DOMRect, pageView: any): void {
        this.dismiss();

        this.popoverEl = pageView.div.createDiv('pf-annotation-popover');
        this.popoverEl.setCssStyles({
            position: 'absolute',
            left: `${rect.left}px`,
            top: `${rect.bottom + 8}px`,
        });

        this.popoverEl.createDiv('pf-popover-header', (el) => {
            el.setText(annotation.type.toUpperCase());
            el.style.color = annotation.color;
        });

        if (annotation.selectedText) {
            this.popoverEl.createDiv('pf-popover-text', el => el.setText(`"${annotation.selectedText.slice(0, 100)}..."`));
        }

        if (annotation.comment) {
            this.popoverEl.createDiv('pf-popover-comment', el => el.setText(annotation.comment));
        }

        if (!annotation.isReadonly) {
            const actions = this.popoverEl.createDiv('pf-popover-actions');
            actions.createEl('button', { text: 'Edit' }, (btn) => {
                btn.onclick = () => this.enableEdit(annotation, pageView);
            });
            actions.createEl('button', { text: 'Delete' }, (btn) => {
                btn.onclick = () => this.deleteAnnotation(annotation.id, pageView);
            });
        } else {
            this.popoverEl.createDiv('pf-popover-readonly', el => {
                el.setText('🔒 Zotero annotation (read-only in PaperForge)');
            });
        }
    }

    dismiss(): void {
        this.popoverEl?.remove();
        this.popoverEl = null;
    }
}
```

## execFile Bridge (in `annotation-fetcher.ts`)

```typescript
import { execFile } from 'child_process';

let currentPaperKey: string = '';

export async function fetchAnnotations(vaultPath: string, pythonExe: string, paperKey: string): Promise<Annotation[]> {
    currentPaperKey = paperKey;
    return runAnnotationCommand(vaultPath, pythonExe, ['list', paperKey, '--json']);
}

export async function createAnnotation(vaultPath: string, pythonExe: string, data: CreatePayload): Promise<Annotation> {
    const args = [
        'create',
        '--paper', data.paperKey,
        '--type', data.type,
        '--page-index', String(data.pageIndex),
        '--selected-text', data.selectedText || '',
        '--comment', data.comment || '',
        '--color', data.color || '#ffd400',
        '--position', JSON.stringify(data.position),
        '--sort-index', data.sortIndex,
        '--json',
    ];
    return runAnnotationCommand(vaultPath, pythonExe, args);
}

async function runAnnotationCommand(vaultPath: string, pythonExe: string, args: string[]): Promise<any> {
    return new Promise((resolve, reject) => {
        execFile(
            pythonExe,
            ['-m', 'paperforge', 'annotation', ...args],
            { cwd: vaultPath, timeout: 15000 },
            (err, stdout) => {
                if (err) {
                    reject(new Error(`Annotation command failed: ${err.message}`));
                    return;
                }
                const result = JSON.parse(stdout);
                if (!result.ok) {
                    reject(new Error(result.error?.message || 'Annotation command failed'));
                    return;
                }
                resolve(result.data);
            }
        );
    });
}
```

## CSS Styles (to add to `styles.css`)

```css
/* Annotation overlay layer */
.pf-annotation-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    z-index: 10;
}

/* Individual annotation rect */
.pf-annotation-rect {
    position: absolute;
    pointer-events: auto;
    cursor: pointer;
    border-radius: 2px;
    transition: opacity 0.15s ease;
}

.pf-annotation-rect:hover {
    opacity: 0.6;
}

.pf-annotation-readonly {
    cursor: default;
}

.pf-annotation-readonly::after {
    content: '🔒';
    position: absolute;
    top: -8px;
    right: -8px;
    font-size: 10px;
    opacity: 0.5;
}

/* Popover */
.pf-annotation-popover {
    position: fixed;
    z-index: 1000;
    background: var(--background-primary);
    border: 1px solid var(--background-modifier-border);
    border-radius: 8px;
    padding: 12px;
    min-width: 200px;
    max-width: 400px;
    box-shadow: var(--shadow-l);
    font-size: var(--font-small);
}

.pf-popover-header {
    font-weight: bold;
    font-size: var(--font-smaller);
    margin-bottom: 8px;
}

.pf-popover-text {
    font-style: italic;
    color: var(--text-muted);
    margin-bottom: 6px;
    padding: 4px 8px;
    border-left: 2px solid var(--background-modifier-border);
}

.pf-popover-comment {
    margin-bottom: 8px;
    white-space: pre-wrap;
}

.pf-popover-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
}

.pf-popover-readonly {
    color: var(--text-faint);
    font-size: var(--font-smallest);
    text-align: center;
    padding: 4px;
}

/* Dark mode adjustments */
.theme-dark .pf-annotation-rect {
    opacity: 0.7;
}
