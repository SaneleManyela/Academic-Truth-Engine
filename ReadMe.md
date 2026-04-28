# Academic Truth Engine

Evidence-first academic Q&A pipeline with hybrid memory, local fusion retrieval, and style-assisted visual outputs.

## Current Workflow Version

Current workflow stages:

1. Initialize console logging helpers for VS Code-friendly output.
2. Run diagnostics for Tesseract and Poppler, including optional `pdf2image` smoke test.
3. Configure Granite 3.1 on Replicate, SSL/certificate guardrails, and embedding fallback chain.
4. Ingest PDF from Google Drive with access checks and endpoint fallback, validate `%PDF-` header, and fall back to OCR text extraction when needed.
5. Build semantic chunks with `SemanticSplitterNodeParser`, stable doc IDs, and hierarchy metadata (`wing`, `room`, `hall`, `drawer_type`).
6. Persist long-term memory to Chroma (`mempalace_db`) via UPSERT ingestion and verify collection growth.
7. Show memory stats dashboard for hierarchy distribution and preview samples.
8. Load local `awesome-notebookLM` styles and initialize visual answer + slide-brief helpers.
9. Load local `QueryRewritingRetrieverPack` (with direct file-path fallback import) in sequential stability mode.
10. Apply runtime visual presets (visual panel / auto brief / auto export).
11. Start interactive research Q&A loop (`end` to stop) with timeout-aware retry handling and optional visual rendering.

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

- `C:\Users\SMANYEL\awesome-notebookLM\README.md`
```

## Local Retriever Pack

The workflow uses `query_rewriting_pack/` as a local package source.

- `QueryRewritingRetrieverPack`
- `HybridFusionRetrieverPack`

In the workflow import stage:

- `llama_index.packs.fusion_retriever.query_rewrite.base.QueryRewritingRetrieverPack`

If standard import fails, it loads `query_rewriting_pack/llama_index/packs/fusion_retriever/query_rewrite/base.py` directly with `importlib`.

## Requirements

### Python

- Python 3.9+
- Jupyter Lab

Primary runtime packages:

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

### System Dependencies (OCR fallback path)

**Current Installation Status:**

| Component | Version | Status | Install Path |
|---|---|---|---|
| Tesseract OCR | 5.5.0.20241111 | ✅ Verified | `C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\` |
| Poppler utilities | 25.12.0 | ✅ Verified | `C:\Program Files\poppler-25.12.0\Library\bin\` |

**OCR Fallback System Check (PowerShell):**

```powershell
# Add Tesseract to PATH (if not already done globally)
$env:Path = "C:\Users\$env:USERNAME\AppData\Local\Programs\Tesseract-OCR;" + $env:Path

# Verify both tools are accessible
tesseract --version      # Expected: "tesseract v5.5.0..." or newer
pdftoppm -v              # Expected: "pdftoppm version 25.12.0" or newer

# If both show version info above, OCR fallback is ready ✅
```

**Installation (if needed):**

Option A (recommended - via winget):
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

Run cells from top to bottom.

## Pre-work (IBM Granite Aligned)

Based on IBM Granite workshop pre-work guidance:

- Run locally or in Google Colab.
- For local execution, ensure `Git` and `Python 3.10/3.11/3.12` are available.
- Set up an AI model runtime before running Q&A steps (Replicate or Ollama).

### Local Pre-work (Windows PowerShell)

Use these commands specifically in **Windows PowerShell**.

1. Open PowerShell and go to the project folder:

```powershell
cd C:\Users\SMANYEL\Academic-Truth-Engine
```

2. Create a virtual environment:

```powershell
python -m venv --upgrade-deps --clear venv
```

3. Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

4. Install runtime components (inside the active venv):

```powershell
pip install jupyter
```

5. Launch runtime:

```powershell
jupyter lab Academic_Truth_Engine_v3.ipynb
```

### Model Serving Pre-work

#### Option A: Replicate (recommended)

1. Create a Replicate account (GitHub account required).
2. Create a Replicate API token.
3. In PowerShell, set the token for your current session:

```powershell
$env:REPLICATE_API_TOKEN = "<your_replicate_api_token>"
```

Note: The workflow relies on Replicate in the model setup and Q&A stages.

#### Option B: Ollama (local model serving)

If you prefer local model serving and your machine has enough resources:

```powershell
ollama serve
```

In another PowerShell window:

```powershell
ollama pull ibm/granite4:micro
```

### Colab Pre-work (alternative)

- Sign in to Google Colab.
- Create/store `REPLICATE_API_TOKEN` in Colab Secrets.
- Enable access to that secret.

## Runtime Configuration

- API token variable used by runtime: `REPLICATE_API_TOKEN`
- If missing, runtime prompts for token with `getpass` fallback to `input`
- Primary notebook: `Academic_Truth_Engine_v3.ipynb`
- Model configured in setup stage:
  - `ibm-granite/granite-3.1-8b-instruct`
  - `temperature=0.1`
  - `context_window=128000`
  - `request_timeout=600.0`
- Embedding fallback chain:
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

Step 5.5 preset options in notebook:

- `visual_only`
- `visual_brief`
- `visual_brief_export`

## Ingestion and Retrieval Flow

1. Paste a Google Drive link.
2. Runtime extracts file ID and tries download via:
   - `https://drive.google.com/uc`
   - `https://drive.usercontent.google.com/download`
3. It handles Google Drive confirm tokens and retries endpoint path on `401/403`.
4. It validates the downloaded file starts with `%PDF-`.
5. It tries PyMuPDF text extraction first.
6. If extracted text is weak, OCR runs and writes `academic_data/source_material.pdf.ocr.txt`.
7. Semantic chunking processes the selected `source_file`.
8. Query-rewriting fusion retriever is initialized.
9. Runtime preset cell can configure visual panel + brief/export behavior before the loop.
10. Q&A answers user questions until `end`, with automatic retry on transient timeout/read-timeout errors.
11. If enabled, each answer auto-renders visually and can auto-generate/export a slide brief JSON.

## Known Notes

- If Drive permissions are restricted, download can fail with `401/403`; set sharing to `Anyone with the link: Viewer`.
- OCR fallback requires both Python OCR packages and system binaries.
- Q&A now retries transient read-timeout failures automatically before returning a timeout message.

## Development Notes

- `query_rewriting_pack/pyproject.toml` currently defines package version `0.5.1`.
- `query_rewriting_pack/README.md` is intentionally minimal and should remain because it is referenced by `pyproject.toml`.
