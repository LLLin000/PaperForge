# Agent Guide for Medical Research Vault

This repository is an Obsidian Vault dedicated to Medical Research (Sports Medicine, Orthopedics). It integrates closely with Zotero and PubMed via MCP tools.

## 0. AGENT PROTOCOL (MANDATORY)

**You possess superhuman capabilities via 147+ specialized skills.** 
Most tasks fail because agents try to "wing it" instead of using the specialized tools provided.

### 🛑 STOP & CHECK: The Skill Audit
**Before executing ANY task, you MUST perform this audit:**

1.  **CLASSIFY**: What is the domain? (Bioinformatics, Clinical, Writing, Dev, Data)
2.  **SCAN**: Look at the [Skill Domain Index](#1-skill-domain-index) below.
3.  **SELECT**: Pick the best tool for the job.
4.  **LOAD**: Execute `skill({ name: "selected-skill" })`.

**Rule of Thumb**: If you are writing Python code for biology, chemistry, or plotting from scratch, **YOU ARE WRONG**. Load a skill instead.

---

## 1. Skill Domain Index

Use this index to quickly find the right tool. 

### 🧬 Bioinformatics & Genomics
| Skill                | Use When...                                                         |
| -------------------- | ------------------------------------------------------------------- |
| `biopython`          | Parsing FASTA/GenBank, BLAST, basic sequence manipulation.          |
| `scanpy` / `anndata` | **Single-cell RNA-seq** analysis, clustering, trajectory inference. |
| `pysam`              | Handling **BAM/SAM/VCF** files (NGS data).                          |
| `deeptools`          | ChIP-seq/ATAC-seq visualization (heatmaps, profiles).               |
| `scvi-tools`         | Deep probabilistic modeling for single-cell data.                   |
| `etetoolkit`         | Phylogenetic trees, evolution, orthology.                           |
| `scikit-bio`         | Microbiome analysis, diversity metrics (UniFrac).                   |

### 🏥 Clinical & Medical
| Skill | Use When... |
|-------|-------------|
| `pubmed-database` | **Literature search**, retrieving abstracts/citations. |
| `clinicaltrials-database` | Searching ClinicalTrials.gov for study protocols/status. |
| `clinical-decision-support` | Generating GRADE-based guidelines or patient cohort analysis. |
| `pyhealth` | Analyzing **EHR data**, clinical prediction models (ICD/CPT). |
| `pydicom` | Reading/processing **DICOM** medical images (CT/MRI). |
| `clinvar-database` | Checking variant pathogenicity/clinical significance. |
| `iso-13485-certification` | Medical device QMS documentation. |

### 🧪 Chemistry & Drug Discovery
| Skill | Use When... |
|-------|-------------|
| `rdkit` / `datamol` | **Cheminformatics**, SMILES parsing, molecule generation. |
| `chembl-database` | Looking up bioactivity data ($IC_{50}$, $K_i$), drug targets. |
| `pubchem-database` | Searching chemical properties, structures by name. |
| `drugbank-database` | Detailed drug pharmacology, interactions, targets. |
| `diffdock` | **Molecular docking** (protein-ligand binding poses). |
| `alphafold-database` | Retrieving 3D protein structures. |

### 📊 Data Science & Statistics
| Skill | Use When... |
|-------|-------------|
| `polars` | Processing **Large DataFrames** (faster than Pandas). |
| `scikit-survival` | **Survival analysis** (Kaplan-Meier, Cox Proportional Hazards). |
| `statistical-analysis` | Performing rigorous statistical tests (ANOVA, t-tests) with APA reporting. |
| `scientific-visualization` | Creating **Publication-Ready** figures (Matplotlib/Seaborn wrappers). |
| `shap` | Explaining ML model predictions (Feature importance). |
| `pymc` | Bayesian modeling and probabilistic programming. |

### ✍️ Writing & Research
| Skill | Use When... |
|-------|-------------|
| `scientific-writing` | Drafting **Full Manuscripts** (IMRAD structure, academic tone). |
| `literature-review` | Conducting systematic reviews across multiple databases. |
| `citation-management` | Finding citations, formatting BibTeX, verifying references. |
| `latex-posters` | Creating conference posters in LaTeX. |
| `research-grants` | Writing NSF/NIH grant proposals. |
| `zotero-lit-review` | **Local Vault Search**. ALWAYS check this before external search. |

### 🛠️ Dev & Automation
| Skill | Use When... |
|-------|-------------|
| `git-master` | Any GIT operation (commit, log, blame). |
| `frontend-ui-ux` | React/Web UI tasks. |
| `playwright` | Browser automation / scraping. |
| `opentrons-integration` | Writing lab automation scripts (OT-2 robots). |

---

## 2. Environment & Tech Stack

- **Platform**: Obsidian (Knowledge Management)
- **Reference Manager**: Zotero (via MCP & Direct SQLite Access)
- **Data Source**: PubMed (via MCP)
- **Primary Language**: Simplified Chinese (简体中文)
- **Scripting**: JavaScript (Handlebars helpers for Templater), Markdown, Python (Zotero interaction)

## 3. Workflows & Commands ("Build/Test")

Since this is a knowledge base, "Build" corresponds to importing and structuring knowledge, and "Test" corresponds to verification.

### Literature Search (The "Build" Loop)
Agents must follow this strict loop when asked to find literature:
1.  **Analyze**: Use `parse_pico` to structure the research question.
2.  **Search**: Use `search_literature` (PubMed) or `zotero-lit-review` (Local Library).
    *   *Constraint*: Always check existing library first using `check_articles_owned`, `search_pubmed_exclude_owned`, or `zotero-lit-review search`.
3.  **Verify**: Use `get_session_pmids` to confirm what was found.
4.  **Import**:
    *   **CRITICAL**: Ask user for Target Collection first (`list_collections`).
    *   Use `batch_import_from_pubmed` for multiple items.
    *   Use `import_from_pmids` for specific items.

### Library Maintenance (The "Lint" Loop)
- **Check Duplicates**: Before adding, always check if PMID exists (`check_articles_owned`).
- **Stats**: Use `get_library_stats` to understand collection size.

## 4. Style Guidelines

### Markdown & Note Structure

Literature notes are generated automatically by the pipeline with standard frontmatter.

**Frontmatter (YAML) is MANDATORY:**
```yaml
---
title: " {{Title}} "
year: {{Year}}
type: {{Type}}
journal: " {{Journal}} "
impact_factor: {{IF}}
category: {{Category}}
tags:
  - 文献阅读
  - {{Subject_Tag}}
keywords: [ {{Keywords}} ]
pdf_link: "[[{{Link_To_PDF}}]]"
---
```

**Content Structure:**
- H1: Title
- H2: 📄 文献基本信息 (Basic Info)
- H2: 💡 文献内容总结 (Summary)
- H2: 🚀 未来方向 (Future Directions)
- H2: 📝 个人备注与补充 (Notes)

### JavaScript (Templater/Handlebars)
- **Location**: `99_System/Template/*.js`
- **Style**: Standard ES6+.
- **Helpers**: Register helpers using `handlebars.registerHelper`.
- **Error Handling**: Fail gracefully (return empty string) if data is missing.

## 5. Interaction Rules

### Language
- **Output**: Simplified Chinese (简体中文) ONLY, unless asked otherwise.
- **Search Terms**: English (for PubMed), but explain in Chinese.

### Protocol
1.  **No Hallucinations**: Never invent PMIDs or citations.
2.  **User Confirmation**:
    -   Confirm **Search Strategy** before executing deep searches.
    -   Confirm **Target Collection** before importing to Zotero.
3.  **Session Awareness**: Use `get_session_summary` to track context.

## 6. Custom Skills

The following skills are installed in `.opencode/skills` and available for complex tasks.
**NOTE: This list is exhaustive. Use the Index in Section 1 for quick lookup.**

(Complete skill list would be here - truncated for brevity)

## 7. External Rules Integration
- **Copilot Instructions**: See `.github/copilot-instructions.md` for detailed MCP tool usage.
- **Workflow**: See `.github/zotero-research-workflow.md` for the authorized PICO -> Search -> Import pipeline.
