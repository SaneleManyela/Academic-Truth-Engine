# Academic Truth Engine

An evidence-first academic question-and-answer pipeline designed for research-heavy document workflows. It combines hybrid memory, local fusion retrieval, OCR fallback, semantic chunking, and visual report generation into a single system for working with academic PDFs and structured source material.

## Overview

Academic Truth Engine is a local research assistant workflow for ingesting, chunking, retrieving, and reasoning over academic content from PDFs and related source material. The system is optimized for:

- Evidence-first answer generation
- Long-term memory persistence with vector storage
- Hybrid retrieval using fusion and query rewriting
- PDF ingestion with Google Drive fallback and OCR recovery
- Semantic document chunking for citation-friendly retrieval
- Optional visual rendering and slide-brief export
- Windows-friendly local setup and notebook execution

The project is designed to help a user load an academic source PDF, retrieve relevant evidence, answer questions grounded in the document, and optionally create visual summaries and structured brief outputs.

## System Goals

The engine emphasizes:

1. Grounded academic answers
   - Answers are expected to rely on source material rather than unverified general knowledge.
   - Retrieval is used before generation so the model sees the document context relevant to the question.

2. Hybrid retrieval and memory
   - Documents are split into semantic chunks.
   - Retrieval uses a fusion-based workflow with query rewriting for stronger matching.
   - Long-term memory is stored in Chroma so repeated workloads can reuse prior ingestion and retrieval state.

3. Robust ingestion
   - PDFs are downloaded from Google Drive when available.
   - File integrity checks verify actual PDF content.
   - If text extraction is weak or the document is scanned, OCR fallback is used.

4. Research automation
   - The system supports interactive Q&A loops.
   - It can render visual panels and auto-generate brief summaries.

5. Local-first flexibility
   - The setup supports local model serving via Ollama or external inference via Replicate.
   - Local assets and custom retriever packs can be used without publishing to a remote package registry.

## Current Workflow Version

The active workflow currently runs in the following stages:

1. Initialize console logging helpers for VS Code-friendly output.
2. Run diagnostics for Tesseract and Poppler, including optional `pdf2image` smoke testing.
3. Configure Granite 3.1 on Replicate, SSL/certificate guardrails, and embedding fallback chain.
4. Ingest PDF from Google Drive with access checks and endpoint fallback, validate `%PDF-` header, and use OCR when plain text extraction is insufficient.
5. Build semantic chunks with `SemanticSplitterNodeParser`, stable document IDs, and hierarchy metadata (`wing`, `room`, `hall`, `drawer_type`).
6. Persist long-term memory to Chroma (`mempalace_db`) via UPSERT ingestion and verify collection growth.
7. Show memory stats dashboard for hierarchy distribution and preview samples.
8. Load local `awesome-notebookLM` styles and initialize visual answer and slide brief helpers.
9. Load local `QueryRewritingRetrieverPack` (with direct file-path fallback import) in sequential stability mode.
10. Apply runtime visual presets (visual panel / auto brief / auto export).
11. Start interactive research Q&A loop (`end` to stop) with timeout-aware retry handling and optional visual rendering.

## High-Level Architecture

The system is a layered pipeline:

- Ingestion layer
  - Accepts a PDF source
  - Validates the file
  - Downloads from Google Drive if needed
  - Uses OCR if the PDF is scanned or low quality

- Document parsing layer
  - Extracts text from PDF content
  - Builds document nodes and chunk metadata
  - Maintains stable IDs and hierarchy labels

- Memory layer
  - Stores chunks in Chroma
  - Supports incremental updates via UPSERT
  - Tracks document distribution by metadata fields

- Retrieval layer
  - Uses query rewriting
  - Combines multiple retrieval strategies in hybrid fusion
  - Returns best sources for a user query

- Reasoning layer
  - Calls the configured LLM
  - Uses retrieved context as evidence
  - Generates final answer with timeout retries and fallback strategies

- Output layer
  - Standard answer output
  - Optional visual panel rendering
  - Optional brief export in structured JSON styles

## Workspace Structure

```text
Academic-Truth-Engine/
|- Academic_Truth_Engine_v3.ipynb
|- Academic_Truth_Engine_v2.ipynb
|- Academic_Truth_Engine_v2_fast_bandwidth_snapshot.ipynb
|- ReadMe.md
|- ReadMeV3.md
|- academic_data/
|  \- source_material.pdf
|- mempalace_db/                     # created automatically after Step 4.5 runs
\- query_rewriting_pack/
   |- pyproject.toml
   |- README.md
   \- llama_index/packs/fusion_retriever/
      |- __init__.py
      |- hybrid_fusion/base.py
      \- query_rewrite/base.py

Local style library path used by Step 4.7:
- C:\Users\SMANYEL\awesome-notebookLM\README.md
```

## Local Retriever Pack

The workflow uses a local package source under `query_rewriting_pack/` to ensure model retrieval logic is available even if the package is not installed normally.

Available local packages:
- `QueryRewritingRetrieverPack`
- `HybridFusionRetrieverPack`

Import path used by the notebook:
- `llama_index.packs.fusion_retriever.query_rewrite.base.QueryRewritingRetrieverPack`

If the standard package import fails, the code falls back to direct loading from:
- `query_rewriting_pack/llama_index/packs/fusion_retriever/query_rewrite/base.py`

This ensures the project still runs in a controlled local environment even if pip-installed packages are incomplete or unavailable.

## Requirements

### Python

- Python 3.9+
- Jupyter Lab

### Primary runtime packages

- `llama-index`
- `llama-index-llms-replicate`
- `llama-index-embeddings-huggingface`
- `llama-index-readers-file`
- `llama-index-packs-fusion-retriever`
- `sentence-transformers`
- `huggingface_hub[hf_xet]`
- `hf_xet`
- `certifi`
- `python-certifi-win32`
- `truststore`
- `nest-asyncio`
- `requests`
- `replicate`
- `pytesseract`
- `pdf2image`
- `Pillow`
- `PyMuPDF`

### System dependencies for OCR fallback

The project includes a document ingestion path that can fall back to OCR when the PDF does not yield good text extraction.

Current installation status:

| Component | Version | Status | Install Path |
|---|---|---|---|
| Tesseract OCR | 5.5.0.20241111 | ✅ Verified | `C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\` |
| Poppler utilities | 25.12.0 | ✅ Verified | `C:\Program Files\poppler-25.12.0\Library\bin\` |

PowerShell system check:

```powershell
# Add Tesseract to PATH (if not already done globally)
$env:Path = "C:\Users\$env:USERNAME\AppData\Local\Programs\Tesseract-OCR;" + $env:Path

# Verify both tools are accessible
tesseract --version      # Expected: "tesseract v5.5.0..." or newer
pdftoppm -v              # Expected: "pdftoppm version 25.12.0" or newer

# If both show version info above, OCR fallback is ready ✅
```

Installation options:

Option A (recommended, via winget):
```powershell
winget install --id UB-Mannheim.TesseractOCR
winget install --id PopperSoftware.Poppler  # or manual from https://poppler.freedesktop.org/
```

Option B (manual):
- Download Tesseract from https://github.com/tesseract-ocr/tesseract/releases
- Download Poppler from https://poppler.freedesktop.org/
- Run installers and ensure bin folders are on PATH

## Quick Start (Windows PowerShell)

```powershell
cd C:\Users\SMANYEL\Academic-Truth-Engine
.\venv\Scripts\Activate.ps1
jupyter lab Academic_Truth_Engine_v3.ipynb
```

Then run the cells from top to bottom.

## Pre-Work

### Local pre-work (IBM Granite aligned)

Based on IBM Granite workshop guidance, the project can run locally or in Google Colab. For local runtimes, it assumes Git and a modern Python version are available.

Local setup on Windows PowerShell:

1. Open PowerShell and move to the project folder:
```powershell
cd C:\Users\SMANYEL\Academic-Truth-Engine
```

2. Create a virtual environment:
```powershell
python -m venv --upgrade-deps --clear venv
```

3. Activate it:
```powershell
.\venv\Scripts\Activate.ps1
```

4. Install the notebook/runtime dependencies:
```powershell
pip install jupyter
```

5. Launch the notebook:
```powershell
jupyter lab Academic_Truth_Engine_v3.ipynb
```

### Model serving pre-work

#### Option A: Replicate (recommended)

1. Create a Replicate account.
2. Generate a Replicate API token.
3. Export it in the current PowerShell session:
```powershell
$env:REPLICATE_API_TOKEN = "<your_replicate_api_token>"
```

The project relies on Replicate for the configured model setup and Q&A stages.

#### Option B: Ollama (local model serving)

If you prefer local model serving:
```powershell
ollama serve
```

Then in another PowerShell window:
```powershell
ollama pull ibm/granite4:micro
```

This allows the project to be adapted to a local inference runtime instead of remote Replicate access.

#### Option C: Google Colab

Alternative setup:
- Sign in to Google Colab
- Store `REPLICATE_API_TOKEN` in Colab Secrets
- Enable access to that secret at runtime

## Runtime Configuration

The workflow uses environment variables and runtime constants to control behavior.

Key runtime variables:
- `REPLICATE_API_TOKEN`
  - Used by the runtime to authenticate to Replicate
  - If missing, the runtime falls back to `getpass`, then `input`

Primary notebook:
- `Academic_Truth_Engine_v3.ipynb`

Configured LLM:
- Model: `ibm-granite/granite-3.1-8b-instruct`
- Temperature: `0.1`
- Context window: `128000`
- Request timeout: `600.0`

Embedding fallback chain:
1. `BAAI/bge-small-en-v1.5`
2. `sentence-transformers/all-MiniLM-L6-v2`
3. `MockEmbedding`

Step 6 runtime toggles:
- `ATE_RUNTIME_MODE` (`fast` default, `deep` optional)
- `ATE_ENABLE_SYNTHESIS` (`1` default, set `0` for evidence-only fast mode)
- `ATE_SOURCE_PRINT_LIMIT` (default `10`)
- `ATE_VISUAL_PANEL` (`1` default)
- `ATE_AUTO_BRIEF` (`0` default)
- `ATE_AUTO_BRIEF_EXPORT` (`0` default)
- `ATE_BRIEF_STYLE` (`artifact` default)

Notebook preset options for Step 5.5:
- `visual_only`
- `visual_brief`
- `visual_brief_export`

## Ingestion and Retrieval Flow

The system follows a clear document-to-answer pipeline:

1. Paste a Google Drive link to the source document.
2. The runtime extracts the file ID and tries to download via:
   - `https://drive.google.com/uc`
   - `https://drive.usercontent.google.com/download`
3. It handles Google Drive confirmation tokens and retries the fallback endpoint path on `401/403` errors.
4. It validates the downloaded file starts with `%PDF-`.
5. It attempts text extraction with PyMuPDF first.
6. If extracted text is weak, it triggers OCR fallback and writes:
   - `academic_data/source_material.pdf.ocr.txt`
7. Semantic chunking processes the source file.
8. Query-rewriting fusion retrieval is initialized.
9. A preset cell can configure visual output and brief/export behavior before the main loop.
10. Q&A runs until the user types `end`.
11. Transient timeout errors are retried before returning a timeout message.
12. If enabled, answers can be auto-rendered visually and a slide brief JSON can be exported.

## Document Processing Details

The engine creates semantic chunks from the source PDF using metadata and hierarchy-aware organization. It preserves structure such as:

- `wing`
- `room`
- `hall`
- `drawer_type`

These metadata fields allow the system to understand document context and maintain a more organized retrieval landscape. It also creates stable document IDs to support updates and avoid duplicate content in persistent vector storage.

## Memory and Persistence

Long-term memory is persisted to Chroma under a collection named:
- `mempalace_db`

The ingestion process performs UPSERT behavior, enabling repeated document loading without unmanaged duplication. The workflow verifies collection growth and displays memory statistics to help monitor the stored data.

This memory layer supports:

- Long-term retention of chunked academic content
- Hierarchical metadata organization
- Collection growth inspection
- Sample preview reporting
- Retrieval and re-use across sessions

## Visual and Brief Generation

The workflow also includes visual components based on a local style library. It loads:
- `C:\Users\SMANYEL\awesome-notebookLM\README.md`

This allows the system to:

- Render a visual answer panel
- Create slide-style briefs
- Export the brief in structured JSON form
- Use artifact-style formatting for brief generation

Runtime toggles can automatically enable:
- visual output
- brief generation
- export to an output artifact

## Q&A Loop Behavior

The interactive research loop is designed for academic exploration:

- Accepts user questions one at a time
- Uses retrieval to find relevant passages
- Sends evidence to the LLM for grounded answer generation
- Retries transient read-timeout failures
- Supports textual and visual answer modes
- Stops when the user inputs `end`

This makes it useful for iterative reading, fact-checking, and evidence-based summarization.

## Known Notes and Operational Guidance

- If Drive permissions are restricted, the download may fail with `401/403`.
  - Set sharing to `Anyone with the link: Viewer`.
- OCR fallback requires both Python OCR packages and system-level Tesseract/Poppler binaries.
- Q&A now automatically retries transient read-timeout failures before returning a timeout response.
- The project is built around a notebook-first workflow, so most execution occurs in a Jupyter environment.
- Local retriever package fallbacks are intentionally included to improve reliability in isolated or partially configured environments.

## Development Notes

- `query_rewriting_pack/pyproject.toml` currently defines package version `0.5.1`.
- `query_rewriting_pack/README.md` is intentionally minimal and should remain because it is referenced by `pyproject.toml`.

## Summary

Academic Truth Engine is a hybrid academic research pipeline that turns a PDF into a searchable, memory-backed, evidence-first research assistant. It is designed for robust ingestion, semantic retrieval, local model compatibility, visual output support, and structured academic reasoning. The workflow is notebook-driven and Windows-friendly, making it suitable for local research experimentation and evidence-grounded Q&A workflows.

This README describes the practical setup, the system architecture, runtime behavior, and the project’s operating assumptions so the workflow can be run and extended reliably.