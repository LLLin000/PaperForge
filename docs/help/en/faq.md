# Frequently Asked Questions

## Why is the library not ready?

The Library module needs three things: a valid Zotero data directory path, a BBT JSON export file in the vault, and a successful sync run.

Check your **Setup → Library** stage to verify the path, ensure Zotero is running and BBT is installed, then re-export the BBT JSON file from Zotero (`File → Export Library → Better BibTeX JSON`). Finally, click **Sync** from the Overview.

---

## Why did OCR extraction fail?

OCR failures typically come from: missing PDF attachments in Zotero, corrupted PDF files, or PaddleOCR API misconfiguration.

Check the OCR Workspace for the paper's status badge — "Failed" indicates a processing error. Try re-running OCR on the specific paper. If failures persist, check your PaddleOCR API key in Setup and ensure the PDF file exists in Zotero.

---

## How do I rebuild the vector index?

Open **Smart Retrieval** from the Overview and click **Build Index**. The index is rebuilt from scratch, re-embedding every paper's full text.

A rebuild may be needed after: adding many new papers, changing the embedding model, or if the index is marked stale. The process streams progress in real time.

---

## How do I update the BBT JSON file?

PaperForge uses a Better BibTeX JSON export of your Zotero library as its paper index source. To update:

1. Open Zotero with the Better BibTeX plugin installed.
2. Right-click your library or collection → **Export Library…**
3. Choose **Better BibTeX JSON** as the format.
4. Save the file to your vault's configured path, overwriting the existing file.
5. In PaperForge, go to Overview and click **Sync Library**.

You only need to re-export when you add, remove, or modify papers in Zotero.

---

## How do I uninstall PaperForge?

Disable the plugin in **Obsidian Settings → Community Plugins → PaperForge**. To fully remove: delete the plugin folder from `.obsidian/plugins/paperforge/` and the PaperForge runtime directory from your vault's System folder.

Your Zotero data, PDFs, and notes are never modified by PaperForge and remain untouched.

---

## Why doesn't PaperForge have built-in literature search capabilities?

1. Current AI Agents still face obstacles in fully retrieving and downloading literature.
2. Human-controlled literature searching and downloading ensures the most complete collection of materials.
3. There are already powerful literature search and download Skills available that work alongside PaperForge.
