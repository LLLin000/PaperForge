# Worktree cleanup archive — paperforge-stabilization

- Path: `D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/paperforge-stabilization`
- Branch: `paperforge-stabilization`
- HEAD: `8dc58ce fix: close review findings for auto-sync, sync PFResult, and global actions`
- Branches containing HEAD:

```
"feat/ocr-structured-pipeline"
"feat/pdf-annotation-layer"
"master"
"paperforge-stabilization"
```

## git status --short

```
 M manifest.json
 M paperforge/__init__.py
 M paperforge/plugin/manifest.json
 M paperforge/worker/vector_db.py
```

## Untracked files

```
(none)
```

## Binary-safe diff

```diff
diff --git a/manifest.json b/manifest.json
index 623492d..d9287d3 100644
--- a/manifest.json
+++ b/manifest.json
@@ -1,7 +1,7 @@
 {
   "id": "paperforge",
   "name": "PaperForge",
-  "version": "1.5.6rc3",
+  "version": "1.5.6rc4",
   "minAppVersion": "1.9.0",
   "description": "Zotero literature pipeline for Obsidian. Sync PDFs, run OCR, and read with AI-assisted deep reading.",
   "author": "Lin Zhaoxuan",
diff --git a/paperforge/__init__.py b/paperforge/__init__.py
index 4ec6722..10b1908 100644
--- a/paperforge/__init__.py
+++ b/paperforge/__init__.py
@@ -1,3 +1,3 @@
 """paperforge — PaperForge package."""
 
-__version__ = "1.5.6rc3"
+__version__ = "1.5.6rc4"
diff --git a/paperforge/plugin/manifest.json b/paperforge/plugin/manifest.json
index 623492d..d9287d3 100644
--- a/paperforge/plugin/manifest.json
+++ b/paperforge/plugin/manifest.json
@@ -1,7 +1,7 @@
 {
   "id": "paperforge",
   "name": "PaperForge",
-  "version": "1.5.6rc3",
+  "version": "1.5.6rc4",
   "minAppVersion": "1.9.0",
   "description": "Zotero literature pipeline for Obsidian. Sync PDFs, run OCR, and read with AI-assisted deep reading.",
   "author": "Lin Zhaoxuan",
diff --git a/paperforge/worker/vector_db.py b/paperforge/worker/vector_db.py
index 6a746ff..1ea7f94 100644
--- a/paperforge/worker/vector_db.py
+++ b/paperforge/worker/vector_db.py
@@ -57,12 +57,11 @@ def _preflight_check(vault, settings: dict) -> dict:
 def get_embed_status(vault) -> dict:
     """Check if vector index exists and has content."""
     from pathlib import Path
-    from paperforge.config import paperforge_paths
-    paths = paperforge_paths(vault)
-    vectors_dir = paths.get("vectors", paths.get("paperforge", Path()) / "vectors")
-    
+    from paperforge.memory.vector_db import get_vector_db_path
+    vectors_dir = get_vector_db_path(vault)
+
     status = {"exists": False, "chunk_count": 0, "collection_name": ""}
-    
+
     if not vectors_dir or not vectors_dir.exists():
         return status
```
