# Academic Truth Engine v3

Evidence-first academic Q&A notebook. Two independent Q&A engines share a single persistent ChromaDB "Memory Palace":

- **Research Loop (Cell 17)** — full-pipeline interactive Q&A with hierarchical memory routing, session persistence, visual panels, and slide brief export.
- **Rapid Paper Q&A (Cell 18)** — ipywidget interface for ad-hoc Q&A against PDFs you upload on the fly, with APA 7th Edition citations and Memory Palace support.

---

## Notebook Cells — What Each One Does

### Cell 1 — Install Dependencies
Installs every Python package the pipeline needs in one `%pip install` command, then patches the Jupyter event loop with `nest_asyncio` so LlamaIndex async calls work inside the kernel without an "event loop already running" error.

**Packages installed:**
`llama-index`, `llama-index-llms-replicate`, `llama-index-embeddings-huggingface`, `llama-index-readers-file`, `llama-index-packs-fusion-retriever`, `llama-index-vector-stores-chroma`, `chromadb`, `sentence-transformers`, `huggingface_hub[hf_xet]`, `hf_xet`, `certifi`, `python-certifi-win32`, `truststore`, `nest-asyncio`, `requests`, `replicate`, `pytesseract`, `pdf2image`, `Pillow`, `PyMuPDF`

**System binaries also required (installed separately):**
- Tesseract OCR — `winget install UB-Mannheim.TesseractOCR` or `choco install tesseract`
- Poppler utils — `choco install poppler`

---

### Cell 2 — Memory Palace Reset
Safety-gated cell that permanently wipes the ChromaDB collection and docstore so you can start fresh with new PDFs.

- **Default state:** `CONFIRM_RESET = False` — runs a dry-run status check only, prints current vector count.
- **To wipe:** change to `CONFIRM_RESET = True`, re-run, type `CONFIRM` at the prompt.
- **Warning:** calling `_system.stop()` on ChromaDB invalidates the Rust bindings for the entire kernel session. After wiping you **must** restart the kernel before running Cell 3 again.

---

### Cell 3 — Batch Ingest (All PDFs in `academic_data/`)
Ingests every individual PDF in the `academic_data/` folder into the Memory Palace in one pass.

- Applies fixed hierarchy labels to all PDFs: `Wing = Academics`, `Room = Adaptive Leadership`, `Hall = Adaptive Leadership`, `Drawer Type = Adv. Dip`.
- Uses UPSERT deduplication — re-running this cell updates existing vectors rather than creating duplicates.
- Skips `source_material.pdf` (the merged copy) to avoid double-ingesting.
- Connects `palace_index`, `palace_collection`, and all palace retriever variables for use by Cells 7, 9, 16, 17, and 18.

---

### Cell 4 — Console Logger + Tesseract Auto-Discovery
Sets up VS Code-friendly logging (no ipywidgets) and locates the Tesseract OCR executable automatically.

- `console_log(msg, level)` — timestamped print function used throughout the notebook.
- `ConsoleHandler` — bridges Python's `logging` module to `console_log`, so LlamaIndex and ChromaDB log output appears in cell output alongside notebook messages.
- `resolve_tesseract_cmd()` — checks env vars, `PATH`, standard Windows install paths, and WinGet package directories; sets `pytesseract.tesseract_cmd` automatically.

---

### Cell 5 — OCR Diagnostics
Verifies the full OCR chain before ingestion:

1. **Tesseract check** — calls `resolve_tesseract_cmd()` and runs `pytesseract.get_tesseract_version()` to confirm the binary is executable, not just present.
2. **Poppler check** — uses `shutil.which("pdftoppm")` / `shutil.which("pdftocairo")` to confirm Poppler is on `PATH`.
3. **End-to-end conversion test** — if `academic_data/source_material.pdf` exists, converts page 1 at 50 DPI via `pdf2image` to verify the full pipeline.

Prints clear `OK` / `WARN` / `ERROR` messages so you know exactly what is working before you spend time on ingestion.

---

### Cell 6 — Configure IBM Granite 3.1 + Embedding Model
Sets up the LLM and embedding model that every later cell uses, and hardens SSL networking.

**LLM — IBM Granite 3.1 8B Instruct (via Replicate):**
- `temperature=0.1` — near-deterministic, factual answers.
- `context_window=128,000` — full Granite 3.1 native token budget.
- `request_timeout=600s` — 10-minute timeout for cold-start containers.
- Academic system prompt — evidence-only mandate, hallucination block, formal prose instruction.
- Replicate SDK patched to enforce 600 s `httpx` read timeout (fixes silent timeout bug in SDK ≥ 0.25).

**Embedding model — three-level fallback chain:**
1. `BAAI/bge-small-en-v1.5` (primary, 384-dim, fast)
2. `sentence-transformers/all-MiniLM-L6-v2` (fallback)
3. `MockEmbedding(384)` (offline last resort — retrieval quality meaningless but pipeline won't crash)

**SSL hardening:** sets `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, `CURL_CA_BUNDLE` to certifi's bundle; loads `certifi_win32` to merge the Windows certificate store for corporate networks.

---

### Cell 7 — Google Drive PDF Downloader
Accepts one or more comma-separated Google Drive share links and downloads each PDF.

**Three-strategy download approach (in order):**
1. `gdown` — handles virus-scan interstitial pages and auth cookies automatically.
2. `requests` via `drive.usercontent.google.com` — 2024-era endpoint with confirm-token extraction.
3. `requests` via legacy `drive.google.com/uc` — fallback for older share links.

**Multi-PDF support:** downloads each link to a numbered part file, then merges all successful PDFs into a single `source_material.pdf` using PyMuPDF. If the merge fails, falls back to text concatenation.

**OCR fallback (`extract_text_or_ocr`):** if PyMuPDF extracts fewer than 50 characters (image-only or scanned PDF), automatically rasterises via `pdf2image` at 300 DPI and runs Tesseract OCR on each page, saving the result as a `.ocr.txt` file.

---

### Cell 8 — Semantic Chunking + Memory Palace Metadata Labelling
Takes the ingested source file and prepares it for Memory Palace storage.

- **`SemanticSplitterNodeParser`** — splits text at natural topic boundaries using cosine-distance between sentence-group embeddings (`buffer_size=3`, `breakpoint_percentile_threshold=95`). Produces coherent, topic-aligned chunks rather than fixed-size cuts.
- **Interactive hierarchy prompts** — asks for `wing`, `room`, `hall`, and `drawer_type` labels (with smart defaults derived from the filename). Press Enter to accept.
- **Stable doc IDs** — assigns deterministic IDs (`filename::doc::N`) required for UPSERT deduplication in Cell 9.
- **Current-document index** — builds an in-memory `VectorStoreIndex` from the current PDF's nodes for fast single-document Q&A (`similarity_top_k=5`, `response_mode=compact`).

---

### Cell 9 — Memory Palace Bridge (Persistent UPSERT Ingestion)
Persists the current document's nodes into ChromaDB (the Memory Palace) with full deduplication.

- Runs `IngestionPipeline` with `DocstoreStrategy.UPSERTS` — re-ingesting the same file updates vectors rather than duplicating them.
- **Fallback Case A:** if the pipeline ran but ChromaDB count didn't increase (a known LlamaIndex edge case), falls back to direct `collection.upsert()` on the pipeline nodes.
- **Fallback Case B:** if the pipeline produced zero nodes AND the collection is empty, bootstraps from the semantic nodes produced in Cell 8 as a safety net.
- Persists the docstore to `mempalace_db/docstore.json` after ingestion.
- Opens `palace_index` and `palace_query_engine` from the populated vector store for use by later cells.
- Handles dead ChromaDB Rust bindings gracefully (prints a kernel-restart instruction instead of crashing).

---

### Cell 10 — Memory Stats Dashboard
Prints a full inventory of the Memory Palace contents without overloading memory.

- Scans up to `DASHBOARD_MAX_SCAN` records (default 1,500; override via env var).
- Reports: total vector count, per-wing distribution, per-room distribution, per-hall distribution, per-drawer-type distribution, and a metadata sample preview.
- Confirms ingestion was successful and shows the complete academic material distribution.

---

### Cell 11 — Label Index Retriever
Two utility functions for exploring and querying the Memory Palace by hierarchy label.

**`get_label_index(collection)`** — scans ChromaDB metadata and prints all unique `(wing, room, hall)` combinations with their associated filenames in a tree layout. Use this to see exactly what is in the palace.

**`retrieve_by_label(wing, room, hall, query, top_k, show_text)`** — fetches stored chunks filtered by any combination of hierarchy labels, with an optional semantic similarity query on top. Accepts any subset of labels — unspecified dimensions are not filtered. Useful for exploring palace contents and verifying retrieval before running the research loop.

---

### Cell 12 — awesome-notebookLM Style Library
Parses a local checkout of the [awesome-notebookLM](https://github.com/ricardokl/awesome-notebookLM) repository and extracts named visual style prompts for the slide brief generator.

- Reads `README.md`, finds every `## Heading` section, extracts the first fenced code block as the style definition.
- Curates six named styles: `editorial`, `minimal`, `magazine`, `neon-tech`, `digital-pop`, `artifact`.
- Exposes `style_library['curated']` dict used by Cell 13's `build_slide_brief()`.
- Path is configurable via the `NOTEBOOKLM_REPO_PATH` environment variable.

---

### Cell 13 — Visual Answer Renderer + Slide Brief Export
Three helper functions called automatically by the research loop after each answer.

**`render_answer_panel(question, result)`** — renders a styled HTML dashboard card inside the notebook output showing the question, full answer, retrieval mode label, and up to 8 source citations with file/hierarchy metadata.

**`build_slide_brief(question, result, style_key)`** — packages a Q&A result into a structured JSON dict containing the question, answer, retrieval mode, a visual style prompt from the awesome-notebookLM library, and a source summary list. Includes strict usage instructions (evidence-only, atomic slide structure, citation traceability) to prevent unsupported synthesis downstream.

**`export_slide_brief(brief)`** — writes a brief dict to `academic_data/visual_briefs/slide_brief_YYYYMMDD_HHMMSS.json`. Each export is a separate timestamped file so no answer is ever overwritten.

---

### Cell 14 — Query Fusion Engine
Loads the local `QueryRewritingRetrieverPack` from the `query_rewriting_pack/` workspace directory.

- Rewrites the user's question into paraphrased variants, retrieves documents for each variant, then fuses and re-ranks results using Reciprocal Rank Fusion (RRF) — improving recall over single-pass retrieval.
- **Sequential stability mode** (`num_queries=1`) is the default: avoids parallel async work inside Jupyter, preventing event loop conflicts.
- Falls back to direct file loading (`importlib.util.spec_from_file_location`) if the standard namespace import fails.
- Operates on the current document's semantic nodes (not the full palace).

---

### Cell 15 — Runtime Visual Preset Switcher
Run immediately before Cell 17 to configure visual and export features for the Q&A session.

**Three presets (set `ATE_PRESET` to one):**

| Preset | HTML Panel | Brief (memory) | Brief (disk) |
|---|---|---|---|
| `visual_only` | ✅ | ✗ | ✗ |
| `visual_brief` | ✅ | ✅ | ✗ |
| `visual_brief_export` | ✅ | ✅ | ✅ |

Sets four environment variables (`ATE_VISUAL_PANEL`, `ATE_AUTO_BRIEF`, `ATE_AUTO_BRIEF_EXPORT`, `ATE_BRIEF_STYLE`) that Cell 17 reads at startup. Default brief style is `artifact`; override with `os.environ["ATE_BRIEF_STYLE"] = "editorial"` etc.

---

### Cell 16 — Batch/Single-Doc Bridge
One-cell bridge that ensures `current_doc_retriever` is always defined regardless of which ingest path was used.

- If `current_doc_index` was set by Cell 8 (single-doc mode): uses it as-is.
- If batch ingest (Cell 3) was used and `current_doc_index` is absent: points `current_doc_index → palace_index` so every query has full cross-document coverage from the palace.
- Builds `current_doc_retriever` with `similarity_top_k=6`.

---

### Cell 17 — Research Loop (Full Interactive Q&A)
The full-featured interactive Q&A engine. Combines short-term retrieval from the current document with long-term cross-document retrieval from the Memory Palace.

**On startup:**
- Choose to continue a saved session or start a new one; sessions are stored as timestamped JSON files in `sessions/`.
- Replicate SDK is monkey-patched with an HTTP fallback (`_http_run_replicate`) that bypasses broken Rust SDK bindings (v1.x) and polls prediction status directly.

**Retrieval pipeline per query:**
1. Keyword-based intent routing maps the question to likely `wing`, `room`, and `hall` labels using `WING_KEYWORD_MAP`, `ROOM_KEYWORD_MAP`, `HALL_KEYWORD_MAP`.
2. Progressive filter relaxation: tries `wing+room+hall` → `wing+room` → `wing` → unfiltered palace search, up to `MAX_FILTER_ATTEMPTS` attempts.
3. Current document retrieval (via `current_doc_retriever` or `query_rewriting_pack`).
4. Both palace and local nodes are merged, deduplicated by node ID, and passed to Granite 3.1 for synthesis.

**Runtime environment toggles (set via env vars or Cell 15):**

| Variable | Default | Effect |
|---|---|---|
| `ATE_RUNTIME_MODE` | `deep` | `fast` reduces `PALACE_TOP_K` (8) and `MAX_FILTER_ATTEMPTS` (3); `deep` uses 12/7 |
| `ATE_ENABLE_SYNTHESIS` | `1` | `0` prints source nodes only, skips LLM |
| `ATE_ENABLE_NETWORK_LLM` | `1` | `0` disables Granite call (offline mode) |
| `ATE_USE_FUSION_PACK` | `0` | `1` uses QueryRewritingRetrieverPack for local-doc retrieval |
| `ATE_SOURCE_PRINT_LIMIT` | `10` | Max source nodes printed per query |
| `ATE_SYNTHESIS_MAX_TOKENS` | `1200` | Granite output token budget (800 in fast mode) |
| `ATE_VISUAL_PANEL` | `1` | Render HTML answer panel |
| `ATE_AUTO_BRIEF` | `0` | Auto-generate slide brief per answer |
| `ATE_AUTO_BRIEF_EXPORT` | `0` | Auto-save brief to disk |
| `ATE_BRIEF_STYLE` | `artifact` | awesome-notebookLM style for briefs |

**Special commands typed in the input prompt:**

| Command | Action |
|---|---|
| `show history` / `session` / `history` | Print all Q&A exchanges for the current session |
| `end` | Save session and exit the loop |
| Any question starting `what is your model` / `what model` | Meta-question: returns model name, memory stats, and runtime config |

**Network error handling:** detects connection failures, SSL errors, and timeouts; shows a clean `🌐 OFFLINE — check network` message instead of a raw traceback.

---

### Cell 18 — Rapid Paper Q&A (ipywidget Interface)
A self-contained widget-based Q&A tool. Upload PDFs on the fly — no need to run the full ingestion pipeline.

**Phase 1 — PDF Selection panel:**
- Paste one local path or Google Drive link per line.
- Click **📂 Index Papers** to download (3-strategy GDrive downloader), extract text (PyMuPDF → pdfplumber → pypdf), chunk with `SentenceSplitter` (512 tokens, 64 overlap), and build an in-memory `VectorStoreIndex`.
- Shows palace connection status (connected vector count or warning if palace isn't loaded).

**Phase 2 — Q&A panel:**
- Eight answer modes, auto-detected from question phrasing or set with a prefix:

| Prefix | Mode | Output format |
|---|---|---|
| *(none / auto)* | `default` | 2–4 flowing prose paragraphs |
| `!short` | `short` | Single tight paragraph ≤ 80 words |
| `!long` | `long` | Full academic prose with opening / body / conclusion |
| `!summarise` | `summarise` | 4–6 structured prose paragraphs |
| `!bullet` | `bullet` | Numbered/bulleted breakdown + summary paragraph |
| `!compare` | `compare` | Comparative prose paragraphs |
| `!define` | `define` | 1–2 definitional prose paragraphs with a direct quote |
| `!critique` | `critique` | Critical analysis prose paragraphs |

- **Dual-source retrieval:** top-6 nodes from the uploaded PDFs (PRIMARY) + top-4 nodes from the Memory Palace (SUPPORTING), passed to Granite 3.1 in a single prompt.
- **APA 7th Edition referencing:** every claim is cited in-text as `(Author, Year, p. XX)` using the filename as the APA hint. A full References section is appended to every answer.
- **Memory Palace sources** are cited using whatever referencing already appears in the chunk text; if none, cited as `(Memory Palace: filename)`.
- **Zero-plagiarism integrity checker:** computes 8-gram overlap between the answer and source nodes. Badges: ✅ < 5% original · ⚠️ 5–15% review · 🚨 > 15% rephrase.
- **Evidence tables:** two collapsible tables show Primary and Supporting source nodes (file, excerpt preview).
- **Session controls:** 📑 History · ? Help · ✕ Clear · 📂 Change PDFs · ○ End Session · 🔄 New Session.

---

## Two-Engine Summary

| Feature | Research Loop (Cell 17) | Rapid Paper Q&A (Cell 18) |
|---|---|---|
| Interface | Interactive text prompt | ipywidget panel |
| PDF input | Pre-ingested into Memory Palace | Upload on the fly (any PDF or Drive link) |
| Memory Palace | PRIMARY retrieval source | SUPPORTING source only |
| Current-doc retrieval | `current_doc_retriever` or fusion pack | In-memory VectorStoreIndex from uploaded PDFs |
| Citation style | Source node metadata (file, hall, snippet) | APA 7th Edition in-text + References section |
| Session persistence | JSON session files in `sessions/` | In-memory history only |
| Visual output | Styled HTML panel + slide brief + JSON export | Evidence tables + integrity badge |
| Modes | Auto-detected prose/essay/retrieval modes | 8 explicitly switchable modes |
| LLM | IBM Granite 3.1 8B via Replicate | IBM Granite 3.1 8B via Replicate |

---

## Architecture

```
PDF(s)
  │
  ├─ Cell 7  ──► Google Drive download (gdown → requests → urllib)
  │              OCR fallback (PyMuPDF → pdf2image + Tesseract)
  │
  ├─ Cell 8  ──► SemanticSplitterNodeParser
  │              Hierarchy metadata (wing / room / hall / drawer_type)
  │              current_doc_index (in-memory, current PDF only)
  │
  └─ Cell 9  ──► IngestionPipeline (UPSERT) ──► ChromaDB mempalace_db/
                  DocstoreStrategy.UPSERTS           academic_palace collection
                  Fallback Case A/B                  palace_index (cross-doc)

Q&A — Research Loop (Cell 17):
  question → intent routing → MetadataFilters (wing/room/hall)
           → palace_index.as_retriever() (progressive filter relaxation)
           → current_doc_retriever / query_rewriting_pack
           → merge + dedup → Granite 3.1 → answer + HTML panel + slide brief

Q&A — Rapid Paper Q&A (Cell 18):
  PDFs → SentenceSplitter → VectorStoreIndex (primary)
  question → primary top-6 + palace top-4 → APA 7th prompt → Granite 3.1
           → prose answer + APA References + integrity badge + evidence tables
```

---

## Hierarchy Metadata

All ingested nodes carry four metadata fields used for routing and filtering:

| Field | Purpose | Example values |
|---|---|---|
| `wing` | Top-level grouping | `Academics`, `Projects`, `People` |
| `room` | Topic grouping inside a wing | `Adaptive_Leadership`, `Case_Studies`, `System_Stats` |
| `hall` | Evidence container inside a room | `Research_Evidence`, `Theory`, `Application` |
| `drawer_type` | Content type tag | `PDF_Text`, `Raw_Text`, `Adv. Dip` |

The Research Loop resolves these from question keywords and tries progressively broader filters until evidence is found.

---

## Workspace Structure

```text
Academic-Truth-Engine/
├── Academic_Truth_Engine_v3.ipynb  ← primary notebook
├── ReadMeV3.md
├── academic_data/
│   ├── source_material.pdf          ← merged PDF (set by Cell 7)
│   └── visual_briefs/               ← slide brief JSON exports (Cell 13)
├── mempalace_db/                    ← ChromaDB persistent store (auto-created)
│   ├── chroma.sqlite3
│   ├── docstore.json
│   └── <uuid>/
├── sessions/                        ← one JSON file per research session
└── query_rewriting_pack/            ← local QueryRewritingRetrieverPack fork
    ├── pyproject.toml
    └── llama_index/packs/fusion_retriever/
        ├── hybrid_fusion/base.py
        └── query_rewrite/base.py
```

---

## Run Order

**First-time setup (new PDFs via Google Drive):**
> Cell 1 → Cell 4 → Cell 5 → Cell 6 → Cell 7 → Cell 8 → Cell 9 → Cell 10 → Cell 12 → Cell 13 → Cell 14 → Cell 15 → Cell 16 → Cell 17

**Batch ingest (all PDFs already in `academic_data/`):**
> Cell 1 → Cell 4 → Cell 6 → Cell 3 → Cell 16 → Cell 17

**Rapid Paper Q&A only (no palace needed):**
> Cell 1 → Cell 6 → Cell 18

**Rapid Paper Q&A with Memory Palace support:**
> Cell 1 → Cell 4 → Cell 6 → Cell 3 (or 7→8→9) → Cell 18

**Wipe and restart palace:**
> Cell 2 (set `CONFIRM_RESET = True`) → **Restart kernel** → Cell 1 → Cell 4 → Cell 6 → Cell 3
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
