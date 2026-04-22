# Installation Guide

## For LLM Agents

If you're an LLM Agent helping set up this literature workflow, welcome. You'll help your user install the pipeline and configure their Zotero/Obsidian integration.

**Tell the user**: Paste this to your agent to auto-configure:
```
Install and configure the literature workflow by following the instructions here:
https://raw.githubusercontent.com/YOUR-USERNAME/YOUR-REPO/main/docs/INSTALLATION.md
```

---

### Step 0: Ask User About Their Setup

Ask the user these questions to determine configuration:

1. **Do you have Zotero installed?**
   - If **yes**: Where is your Zotero data directory? (usually `C:\Users\<User>\Zotero` on Windows or `~/Zotero` on macOS/Linux)
   - If **no**: Install Zotero first from https://www.zotero.org/download/ and install the **Better BibTeX** plugin

2. **Is your Zotero storage directory in a different location?**
   - Default: same as data directory
   - If **different path**: ask for the full path to the `storage` folder

3. **Do you have Obsidian installed?**
   - If **yes**: Where is your vault located? (e.g., `D:\L\Med\Research`)
   - If **no**: Ask them to install Obsidian and create a vault first

4. **Do you have a PaddleOCR API key?**
   - If **yes**: ask for the API key
   - If **no**: Direct them to https://paddleocr.baidu.com/ to apply for one

5. **Do you have Python 3.10+ installed?**
   - If **yes**: proceed
   - If **no**: Ask them to install Python 3.10+ from https://python.org

**Configuration summary**:
- Zotero path: `{zotero_path}`
- Zotero storage path: `{storage_path}` (may equal zotero_path)
- Obsidian vault path: `{vault_path}`
- PaddleOCR API key: `{ocr_api_key}`

---

### Step 1: Install Dependencies

Run in the terminal (spawn a subagent if needed):

```bash
pip install requests pymupdf pillow pytest
```

If using Poetry:
```bash
poetry add requests pymupdf pillow pytest
```

---

### Step 2: Create Directory Structure

Create the following directories in the Obsidian vault:

```bash
mkdir -p "{vault_path}/99_System/PaperForge/ocr"
mkdir -p "{vault_path}/99_System/PaperForge/worker/scripts"
mkdir -p "{vault_path}/99_System/Zotero"
mkdir -p "{vault_path}/03_Resources/Literature"
mkdir -p "{vault_path}/00_Inbox"
```

---

### Step 3: Configure Zotero Integration

#### Option A: Junction/Symlink (Recommended)

**Windows** (admin terminal):
```cmd
mklink /J "{vault_path}\99_System\Zotero" "{zotero_path}"
```

**macOS/Linux**:
```bash
ln -s "{zotero_path}" "{vault_path}/99_System/Zotero"
```

#### Option B: Config file (if symlink not possible)

Create `{vault_path}/.env`:
```
ZOTERO_DATA_DIR={zotero_path}
ZOTERO_STORAGE_DIR={storage_path}
```

---

### Step 4: Configure OCR Pipeline

Create `{vault_path}/.env` (or append if exists):
```
PADDLEOCR_API_KEY={ocr_api_key}
PADDLEOCR_API_URL=https://paddleocr.baidu.com/api/v1/ocr
```

---

### Step 5: Install Workflow Scripts

Copy the following files from the repository to your vault:

```bash
# Copy scripts
cp -r scripts/* "{vault_path}/99_System/PaperForge/worker/scripts/"

# Copy AGENTS.md
cp AGENTS.md "{vault_path}/AGENTS.md"
```

---

### Step 6: Verify Setup

Run validation:

```bash
cd "{vault_path}"
python 99_System/PaperForge/worker/scripts/validate_setup.py
```

This checks:
- [ ] Zotero SQLite accessible
- [ ] OCR directory writable
- [ ] Required Python packages installed
- [ ] AGENTS.md exists
- [ ] Directory structure correct

---

### Step 7: Configure AGENTS.md

Edit `{vault_path}/AGENTS.md`:

1. Update the vault path references
2. Set your preferred output language (default: Simplified Chinese)
3. Configure any custom collection paths

---

## For Humans

### Quick Start

1. **Prerequisites**:
   - Python 3.10+
   - Zotero + Better BibTeX plugin
   - Obsidian
   - PaddleOCR API key

2. **Run the installer**:
   ```bash
   python setup.py
   ```
   This interactive script will ask you the same questions as above and configure everything automatically.

3. **Verify**:
   ```bash
   python 99_System/PaperForge/worker/scripts/validate_setup.py
   ```

---

## Troubleshooting

### Zotero not found
- Ensure Zotero is installed
- Check the data directory path (Edit → Preferences → Advanced → Files and Folders)

### Permission denied on Windows
- Run terminal as Administrator for junction creation
- Or use Option B (config file) instead

### Better BibTeX not installed
- In Zotero: Tools → Plugins → Install plugin from file
- Download from https://github.com/retorquere/zotero-better-bibtex/releases

---

## Next Steps

After installation:

1. **Index your library**: Run the index-refresh worker to create formal notes for existing papers
2. **Queue papers for analysis**: Use the Base system to mark papers for deep reading
3. **Run OCR**: The OCR worker processes queued papers automatically
4. **Start deep reading**: Use `/LD-deep <zotero_key>` to generate structured reading notes

Read the [Workflow Guide](../README.md) for detailed usage instructions.
