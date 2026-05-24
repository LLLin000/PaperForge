# Zotero Annotation SQLite Schema Report

> Status: COMPLETE | Source: zotero/zotero (main branch)

## Table: itemAnnotations

```sql
CREATE TABLE itemAnnotations (
    itemID INTEGER PRIMARY KEY,
    parentItemID INT NOT NULL,
    type INTEGER NOT NULL,
    authorName TEXT,
    text TEXT,
    comment TEXT,
    color TEXT,
    pageLabel TEXT,
    sortIndex TEXT NOT NULL,
    position TEXT NOT NULL,
    isExternal INT NOT NULL,
    FOREIGN KEY (itemID) REFERENCES items(itemID) ON DELETE CASCADE,
    FOREIGN KEY (parentItemID) REFERENCES itemAttachments(itemID)
);
CREATE INDEX itemAnnotations_parentItemID ON itemAnnotations(parentItemID);
```

## Annotation Type Mapping

| Integer | String      | Description          |
|---------|-------------|----------------------|
| 1       | `highlight` | Text highlight       |
| 2       | `note`      | Sticky note          |
| 3       | `image`     | Image region capture |
| 4       | `ink`       | Freehand drawing     |
| 5       | `underline` | Text underline       |
| 6       | `text`      | Text box (resizable) |

Source: `chrome/content/zotero/xpcom/annotations.js`
```javascript
Zotero.Annotations.ANNOTATION_TYPE_HIGHLIGHT = 1;
Zotero.Annotations.ANNOTATION_TYPE_NOTE      = 2;
Zotero.Annotations.ANNOTATION_TYPE_IMAGE     = 3;
Zotero.Annotations.ANNOTATION_TYPE_INK       = 4;
Zotero.Annotations.ANNOTATION_TYPE_UNDERLINE = 5;
Zotero.Annotations.ANNOTATION_TYPE_TEXT      = 6;
```

## Position JSON Structures

### Highlight / Underline / Note / Text (type 1, 2, 5, 6)
```json
{
    "pageIndex": 1,
    "rects": [
        [231.284, 402.126, 293.107, 410.142],
        [54.222, 392.164, 293.107, 400.18]
    ]
}
```
Each rect: `[left, top, right, bottom]` in PDF points (1/72 inch), origin bottom-left.

### Image (type 3)
```json
{
    "pageIndex": 123,
    "rects": [[314.4, 412.8, 556.2, 609.6]],
    "width": 400,
    "height": 200
}
```

### Ink (type 4)
```json
{
    "pageIndex": 1,
    "width": 2,
    "paths": [
        [x0, y0, x1, y1, x2, y2, ...],
        [x3, y3, x4, y4, ...]
    ]
}
```

## Key Fields

| Column            | Type     | Notes                                         |
|-------------------|----------|-----------------------------------------------|
| `text`            | TEXT     | Extracted text for highlight/underline only   |
| `comment`         | TEXT     | User's annotation note (may contain HTML)     |
| `color`           | TEXT     | Hex color, e.g. `#ffd400` (default yellow)    |
| `pageLabel`       | TEXT     | Page label string, e.g. "15", "XVI"           |
| `sortIndex`       | TEXT     | Zero-padded: `"<page:05d>|<rect:06d>|<char:05d>"` |
| `position`        | TEXT     | JSON string (can be up to 65KB before split)  |
| `isExternal`      | INT      | 1 = embedded PDF annotation (read-only)       |

## Relationship Traversal

```sql
-- Get all annotations for a paper (top-level item)
SELECT
    ia.itemID,
    ia.type,
    ia.text,
    ia.comment,
    ia.color,
    ia.pageLabel,
    ia.sortIndex,
    ia.position,
    ia.isExternal,
    i.key AS annotation_key,
    i.dateModified,
    i.libraryID,
    att.path AS attachment_path,
    att.key AS attachment_key,
    att.linkMode AS attachment_link_mode
FROM items paper
JOIN items att ON att.parentItemID = paper.itemID
    AND att.itemTypeID = (SELECT itemTypeID FROM itemTypes WHERE typeName = 'attachment')
JOIN itemAnnotations ia ON ia.parentItemID = att.itemID
JOIN items i ON i.itemID = ia.itemID
WHERE paper.key = ?;

-- Get tags for annotations
SELECT
    i.key AS annotation_key,
    t.name AS tag_name
FROM items i
JOIN itemTags it ON it.itemID = i.itemID
JOIN tags t ON t.tagID = it.tagID
WHERE i.key IN (?);
```

## Annotation Color Presets

Source: `zotero/reader/src/common/defines.js`
```javascript
const ANNOTATION_COLORS = [
    ['yellow',  '#ffd400'],
    ['red',     '#ff6666'],
    ['green',   '#5fb236'],
    ['blue',    '#2ea8e5'],
    ['purple',  '#a28ae5'],
    ['magenta', '#e56eee'],
    ['orange',  '#f19837'],
    ['gray',    '#aaaaaa'],
];
```

## Position Size Limit

`ANNOTATION_POSITION_MAX_SIZE = 65000` bytes. Annotations whose serialized `position` JSON exceeds this are split into multiple annotation items (by rect or path segment).

## Important: Read-Only Access Only

Zotero documentation explicitly warns:
> "access to the SQLite database should be done only in a read-only manner. Modifying the database while Zotero is running can easily result in a corrupted database."

PaperForge must:
1. COPY `zotero.sqlite` to a temp path before reading (if Zotero is running)
2. Never write to any Zotero SQLite table
3. Never assume schema stability across Zotero versions
