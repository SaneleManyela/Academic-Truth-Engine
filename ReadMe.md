# Academic Truth Engine

Evidence-first academic Q&A pipeline built around `Academic_Truth_Engine_v2.ipynb` and a local fusion retriever pack.

## Current Notebook Version

`Academic_Truth_Engine_v2.ipynb` runs as an 8-cell workflow:

1. Install runtime dependencies with `%pip` (LlamaIndex, Replicate, embedding, OCR, trust/cert packages).
2. Initialize console logging helpers for VS Code-friendly output.
3. Run diagnostics for Tesseract and Poppler, including optional `pdf2image` smoke test.
4. Configure Granite 3.1 on Replicate, SSL/certificate guardrails, and embedding fallback chain.
5. Ingest PDF from Google Drive with access checks and endpoint fallback, validate `%PDF-` header, and fall back to OCR text extraction when needed.
6. Build semantic chunks with `SemanticSplitterNodeParser` and attach source metadata.
7. Load local `QueryRewritingRetrieverPack` (with direct file-path fallback import) and create retriever pipeline.
8. Start interactive research Q&A loop (`end` to stop) with timeout-aware retry handling.

## Workspace Structure

```text
Academic-Truth-Engine/
|- Academic_Truth_Engine_v2.ipynb
|- ReadMe.md
|- academic_data/
|  \- source_material.pdf
\- query_rewriting_pack/
   |- pyproject.toml
   |- README.md
   \- llama_index/packs/fusion_retriever/
      |- __init__.py
      |- hybrid_fusion/base.py
      \- query_rewrite/base.py
```

## Local Retriever Pack

The notebook uses `query_rewriting_pack/` as a local package source.

- `QueryRewritingRetrieverPack`
- `HybridFusionRetrieverPack`

In the notebook, Step 5 imports:

- `llama_index.packs.fusion_retriever.query_rewrite.base.QueryRewritingRetrieverPack`

If standard import fails, it loads `query_rewriting_pack/llama_index/packs/fusion_retriever/query_rewrite/base.py` directly with `importlib`.

## Requirements

### Python

- Python 3.9+
- Jupyter Notebook or Jupyter Lab

Primary runtime packages installed in Step 1:

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

- Tesseract OCR executable: https://github.com/tesseract-ocr/tesseract
- Poppler utilities (`pdftoppm` or `pdftocairo`): https://poppler.freedesktop.org/

Optional Windows install via Chocolatey:

```powershell
choco install tesseract
choco install poppler
```

## Quick Start (Windows PowerShell)

```powershell
cd C:\Users\SMANYEL\Academic-Truth-Engine
.\venv\Scripts\Activate.ps1
jupyter notebook Academic_Truth_Engine_v2.ipynb
```

Run cells from top to bottom.

## Notebook Pre-work (IBM Granite Aligned)

Based on IBM Granite workshop pre-work guidance:

- Run notebooks locally or in Google Colab.
- For local execution, ensure `Git` and `Python 3.10/3.11/3.12` are available.
- Set up an AI model runtime before running notebook Q&A steps (Replicate or Ollama).

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

4. Install Jupyter components (inside the active venv):

```powershell
python -m pip install --require-virtualenv notebook ipywidgets
```

5. Launch the notebook:

```powershell
jupyter notebook Academic_Truth_Engine_v2.ipynb
```

### Model Serving Pre-work

#### Option A: Replicate (recommended for this notebook)

1. Create a Replicate account (GitHub account required).
2. Create a Replicate API token.
3. In PowerShell, set the token for your current session:

```powershell
$env:REPLICATE_API_TOKEN = "<your_replicate_api_token>"
```

Note: This notebook relies on Replicate in Step 2 and Step 6.

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
- Enable notebook access to that secret.

## Runtime Configuration

- API token variable used by notebook: `REPLICATE_API_TOKEN`
- If missing, notebook prompts for token with `getpass` fallback to `input`
- Model configured in Step 2:
  - `ibm-granite/granite-3.1-8b-instruct`
  - `temperature=0.1`
  - `context_window=128000`
  - `request_timeout=600.0`
- Embedding fallback chain:
  1. `BAAI/bge-small-en-v1.5`
  2. `sentence-transformers/all-MiniLM-L6-v2`
  3. `MockEmbedding`

## Ingestion and Retrieval Flow

1. Paste a Google Drive link.
2. Notebook extracts file ID and tries download via:
   - `https://drive.google.com/uc`
   - `https://drive.usercontent.google.com/download`
3. It handles Google Drive confirm tokens and retries endpoint path on `401/403`.
4. It validates the downloaded file starts with `%PDF-`.
5. It tries PyMuPDF text extraction first.
6. If extracted text is weak, OCR runs and writes `academic_data/source_material.pdf.ocr.txt`.
7. Step 4 chunks the selected `source_file` semantically.
8. Step 5 builds the query-rewriting fusion retriever.
9. Step 6 answers user questions until `end`, with automatic retry on transient timeout/read-timeout errors.

## Known Notes

- If Drive permissions are restricted, download can fail with `401/403`; set sharing to `Anyone with the link: Viewer`.
- OCR fallback requires both Python OCR packages and system binaries.
- Step 6 now retries transient read-timeout failures automatically before returning a timeout message.

## Development Notes

- `query_rewriting_pack/pyproject.toml` currently defines package version `0.5.1`.
- `query_rewriting_pack/README.md` is intentionally minimal and should remain because it is referenced by `pyproject.toml`.
