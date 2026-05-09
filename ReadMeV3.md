# Academic Truth Engine v3

Evidence-first academic Q&A pipeline with hybrid memory:

- Short-term grounding from the current PDF via local query-rewriting fusion retrieval.
- Long-term grounding across prior PDFs via a persistent ChromaDB "Memory Palace" store.

## v3 Notebook

Primary runtime notebook:

- `Academic_Truth_Engine_v3.ipynb`

Current v3 stages:

1. Install runtime dependencies (LlamaIndex, Granite/Replicate support, OCR stack, Chroma integration).
2. Initialize VS Code-friendly console logging.
3. Run OCR diagnostics for Tesseract and Poppler.
4. Configure Granite 3.1 and embedding fallback chain.
5. Ingest a PDF from Google Drive with permission-aware retries and OCR fallback.
6. Chunk content semantically and attach source metadata.
7. Add hierarchical metadata (`wing`, `room`, `hall`, `drawer_type`) and stable document IDs for traceability.
8. Persist nodes to Memory Palace (`mempalace_db`) using UPSERT ingestion to avoid duplicates.
9. Print a memory stats dashboard (collection count + wing/room/hall/drawer distributions + metadata sample).
10. Initialize local `QueryRewritingRetrieverPack` in sequential mode for stability.
11. Apply runtime visual presets via Step 5.5 (`visual_only`, `visual_brief`, `visual_brief_export`).
12. Run interactive Q&A that synthesizes short-term and long-term evidence with hierarchical routing and semantic citations.
    - On startup, choose to **continue a previous session** or **start a new session**.
    - Six auto-detected **prompt modes**: `essay`, `chat`, `summarise`, `paraphrase`, `formulate`, `retrieval`.
    - Built-in **meta-question** handler for system self-knowledge (model name, memory stats, etc.).
    - **Network error** detection: shows a clean `🌐 OFFLINE` message instead of raw tracebacks.
    - Type `show history` (or `session`/`history`) to view all Q&A exchanges for the current session.
    - Type `end` to exit the loop.
13. Optionally auto-render visual answer panels and auto-generate/export slide briefs per query.

## Architecture Summary

v3 shifts the engine from temporary-only memory to persistent memory:

1. Ingest: PDF -> semantic nodes.
2. Memorize: nodes -> persistent Chroma collection (`academic_palace`) via UPSERTS.
3. Retrieve:
  - Current-doc retrieval via `QueryRewritingRetrieverPack`.
  - Cross-doc retrieval via hall-prioritized palace routing when question intent matches known halls.
4. Synthesize: Granite 3.1 composes one evidence-first answer from both contexts.
5. Trace: source nodes are printed with file name, hall, and text snippet.

Hierarchy-aware routing:

- Step 6 infers `wing`, `room`, and `hall` targets from question intent.
- Retrieval attempts progressively specific filters first (for example `wing+room+hall`), then relaxes to broader filters.
- If no filtered route returns evidence, retrieval falls back to general palace search.

Hierarchy metadata currently captured during ingestion:

- `wing`: top-level memory grouping such as `Projects` or `People`
- `room`: topic grouping inside a wing
- `hall`: evidence grouping used for current routing logic
- `drawer_type`: raw evidence type such as `PDF_Text` or `Raw_Text`

This enables cross-document questions such as comparing concepts from this week and last week.

## Workspace Structure

```text
Academic-Truth-Engine/
|- Academic_Truth_Engine_v3.ipynb
|- ReadMeV3.md
|- academic_data/
|  \- source_material.pdf
|- mempalace_db/                     # created automatically after Step 4.5 runs
|- sessions/                         # created automatically; one JSON file per session
\- query_rewriting_pack/
  |- pyproject.toml
  |- README.md
  \- llama_index/packs/fusion_retriever/
    |- __init__.py
    |- hybrid_fusion/base.py
    \- query_rewrite/base.py
```

## Core Dependencies

Installed by Step 1 in v3:

- `llama-index`
- `llama-index-llms-replicate`
- `llama-index-embeddings-huggingface`
- `llama-index-readers-file`
- `llama-index-packs-fusion-retriever`
- `llama-index-vector-stores-chroma`
- `chromadb`
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

## OCR System Requirements (Windows)

Verified setup:

| Component | Version | Status | Install Path |
|---|---|---|---|
| Tesseract OCR | 5.5.0.20241111 | Verified | `C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\` |
| Poppler utilities | 25.12.0 | Verified | `C:\Program Files\poppler-25.12.0\Library\bin\` |

Quick check:

```powershell
tesseract --version
pdftoppm -v
```

## Quick Start (Windows PowerShell)

```powershell
cd C:\Users\SMANYEL\Academic-Truth-Engine
.\venv\Scripts\Activate.ps1
jupyter lab Academic_Truth_Engine_v3.ipynb
```

Run all cells from top to bottom.

## MemPalace Integration Notes

You already cloned and synced MemPalace separately. That is useful for MCP tooling and standalone experimentation.

For this notebook, persistence is handled directly by Chroma using:

- `PALACE_DB_PATH` (default: `./mempalace_db`)
- `PALACE_COLLECTION` (default: `academic_palace`)

Ingestion behavior:

- Uses `IngestionPipeline` with `DocstoreStrategy.UPSERTS`.
- Uses stable `doc_id` values (`<file_name>::doc::<index>`) to prevent duplicate vectors when the same source is re-run.
- Persists docstore state at `mempalace_db/docstore.json` so UPSERT behavior survives restarts.
- Adds hierarchy metadata (`wing`, `room`, `hall`, `drawer_type`) for hierarchical memory routing.

Optional PowerShell overrides before launching Jupyter:

```powershell
$env:PALACE_DB_PATH = "C:\Users\SMANYEL\Academic-Truth-Engine\mempalace_db"
$env:PALACE_COLLECTION = "academic_palace"
```

## Runtime Configuration

- Required token: `REPLICATE_API_TOKEN`
- Granite model: `ibm-granite/granite-3.1-8b-instruct`
- Typical inference settings:
  - `temperature=0.1`
  - `context_window=128000`
  - `request_timeout=600.0`
- Query runtime mode: `ATE_RUNTIME_MODE` (`fast` default, `deep` optional)
- Optional synthesis toggle: `ATE_ENABLE_SYNTHESIS` (`1` default, set `0` for evidence-only fast mode)
- Source print cap: `ATE_SOURCE_PRINT_LIMIT` (default `10`)
- Dashboard scan cap: `PALACE_DASHBOARD_MAX_SCAN` (default `1500`)
- Dashboard preview size: `PALACE_DASHBOARD_PREVIEW_LIMIT` (default `8`)
- Visual panel toggle: `ATE_VISUAL_PANEL` (`1` default)
- Auto brief toggle: `ATE_AUTO_BRIEF` (`0` default)
- Auto brief export toggle: `ATE_AUTO_BRIEF_EXPORT` (`0` default)
- Auto brief style key: `ATE_BRIEF_STYLE` (`artifact` default)

Step 5.5 preset switcher options in notebook:

- `visual_only`
- `visual_brief`
- `visual_brief_export`

Set token in PowerShell:

```powershell
$env:REPLICATE_API_TOKEN = "<your_replicate_api_token>"
$env:ATE_RUNTIME_MODE = "fast"
# Optional: $env:ATE_ENABLE_SYNTHESIS = "0"
# Optional: $env:PALACE_DASHBOARD_MAX_SCAN = "2500"
# Optional visual controls:
# $env:ATE_VISUAL_PANEL = "1"
# $env:ATE_AUTO_BRIEF = "1"
# $env:ATE_AUTO_BRIEF_EXPORT = "0"
# $env:ATE_BRIEF_STYLE = "artifact"
```

## Prompt Modes

Cell 17 auto-detects the intent of each query and selects a prompt mode:

| Mode | Trigger keywords | Behaviour |
|---|---|---|
| `essay` | `write`, `essay`, `discuss`, `analyse` | Long-form academic paragraph |
| `chat` | `what is`, `who`, `when`, `how many` | Short direct factual answer |
| `summarise` | `summarise`, `summarize`, `summary`, `tldr` | Concise bullet-point summary |
| `paraphrase` | `paraphrase`, `reword`, `rephrase` | Plain-language restatement |
| `formulate` | `formulate`, `structure`, `framework` | Structured evidence-based argument |
| `retrieval` | (default fallback) | Evidence retrieval with synthesis |

## Session History

Every Q&A exchange is persisted to `sessions/` as a JSON file.

- On Cell 17 startup the engine checks for previous sessions in `sessions/`.
- If found, it prints the most recent session ID and exchange count, then asks:
  - `c` — **continue** the previous session (appends new Q&A to it)
  - `n` — **new session** (creates a fresh `session_YYYYMMDD_HHMMSS.json`)
- During the loop, type `show history` (or `session` / `history`) to view all exchanges in the current session as a styled HTML panel.
- Session files are plain JSON and can be inspected or archived freely.

## Visual Output Panel

All answers are rendered in a dark-theme HTML panel:

- **Background**: `#0a0a0a` (near-black)
- **Text**: `#f0f0f0` / `#e8e8e8` (white / near-white)
- **Borders**: top + bottom in **gold** (`#CFB53B`), left + right in **blue** (`#1A6FBF`)
- **Answer body**: `#111111` box with a gold left stripe and a faint blue glow
- **Source citations**: steel-blue `#8ab0c8`

The `show history` panel uses the same dark CSS template.

## Known Notes

- Google Drive files must be shared as `Anyone with the link: Viewer` for reliable download.
- OCR fallback requires both Python packages and system binaries.
- Hall labels are prompted during Step 4; keep labels consistent (for example `Adaptive_Leadership`, `Case_Study`, `Systems_Thinking`) to improve retrieval precision.
- Hybrid Q&A may take longer than v2/v3 temporary-only retrieval because it queries multiple contexts.
- In `fast` mode, Step 6 limits hierarchy-filter attempts and caches filtered query engines to reduce repeated overhead.
- If Step 5.5 is used, run it immediately before Step 6 so the selected preset values are applied to the loop.

## Development Notes

- `query_rewriting_pack/pyproject.toml` currently defines package version `0.5.1`.
- `query_rewriting_pack/README.md` remains intentionally minimal because it is referenced by `pyproject.toml`.
