# Academic Truth Engine

Evidence-first academic Q&A pipeline built around `Academic_Truth_Engine_v2.ipynb` and a local fusion retriever pack.

## Current Notebook Version

`Academic_Truth_Engine_v2.ipynb` now runs as an 8-cell workflow (plus one scratch cell at the end):

1. Install runtime dependencies with `%pip` (LlamaIndex, Replicate, embedding, OCR, trust/cert packages).
2. Initialize console logging helpers for VS Code-friendly output.
3. Run diagnostics for Tesseract and Poppler, including optional `pdf2image` smoke test.
4. Configure Granite 3.1 on Replicate, SSL/certificate guardrails, and embedding fallback chain.
5. Ingest PDF from Google Drive, validate `%PDF-` header, and fall back to OCR text extraction when needed.
6. Build semantic chunks with `SemanticSplitterNodeParser` and attach source metadata.
7. Load local `QueryRewritingRetrieverPack` (with direct file-path fallback import) and create retriever pipeline.
8. Start interactive research Q&A loop (`end` to stop).

Extra cell currently present:

- Final cell contains raw text (`What is adaptive leadership`) and is not executable Python. Leave it unrun or remove it.

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

## Runtime Configuration

- API token variable used by notebook: `REPLICATE_API_TOKEN`
- If missing, notebook prompts for token with `getpass` fallback to `input`
- Model configured in Step 2:
  - `ibm-granite/granite-3.1-8b-instruct`
  - `temperature=0.1`
  - `context_window=128000`
  - `request_timeout=300.0`
- Embedding fallback chain:
  1. `BAAI/bge-small-en-v1.5`
  2. `sentence-transformers/all-MiniLM-L6-v2`
  3. `MockEmbedding`

## Ingestion and Retrieval Flow

1. Paste a Google Drive link.
2. Notebook extracts file ID and downloads from `https://drive.google.com/uc`.
3. It validates the downloaded file starts with `%PDF-`.
4. It tries PyMuPDF text extraction first.
5. If extracted text is weak, OCR runs and writes `academic_data/source_material.pdf.ocr.txt`.
6. Step 4 chunks the selected `source_file` semantically.
7. Step 5 builds the query-rewriting fusion retriever.
8. Step 6 answers user questions until `end`.

## Known Notes

- If Drive permissions are restricted, download may return HTML instead of PDF.
- OCR fallback requires both Python OCR packages and system binaries.
- Final Q&A print label still says `Granite 3.0`, while actual configured model is Granite 3.1.

## Development Notes

- `query_rewriting_pack/pyproject.toml` currently defines package version `0.5.1`.
- `query_rewriting_pack/README.md` is intentionally minimal and should remain because it is referenced by `pyproject.toml`.
