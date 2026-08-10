# Academic Truth Engine v3 — Notebook Documentation

## 1. High-Level Purpose

This notebook is a **local, evidence-grounded research assistant pipeline** built around LlamaIndex, ChromaDB, and IBM Granite 3.1 (via Replicate). Its job is to take a corpus of academic PDFs, index them into a persistent, hierarchically-labelled vector store (the "Memory Palace"), and let the user ask natural-language research questions that are answered **only** from that indexed evidence — with source citations and safeguards against hallucination.

At a system level it does four things:

1. **Ingest** — pull PDFs in (either one-by-one from Google Drive links, or in bulk from a local folder), extract text (with OCR fallback for scanned documents), and normalise them into LlamaIndex `Document` objects.
2. **Index** — semantically chunk the documents and store them as embeddings in ChromaDB, tagged with a four-level metadata hierarchy (`wing` / `room` / `hall` / `drawer_type`) so material can later be filtered or browsed by topic/category rather than just similarity.
3. **Retrieve & Answer** — route a user's question through whichever query engine is available (single-document index, query-fusion retriever, or the full persistent Memory Palace), pull back the most relevant chunks, and pass them to Granite 3.1 with a strict "evidence-only, no hallucination" system prompt.
4. **Present** — surface the answer through one of several Jupyter widget-based chat UIs, optionally rendering a styled HTML answer panel and/or exporting a structured "slide brief" JSON for downstream slide-generation tools.

The notebook is explicitly designed to be **resilient and restart-tolerant**: nearly every cell checks whether its prerequisites already exist in `globals()` before doing work, and several cells contain explicit guard/repair logic for a known ChromaDB failure mode (see §4).

---

## 2. Pipeline Overview

```
Cell 1  → Install dependencies, patch asyncio for Jupyter
Cell 2  → (Optional/manual) Memory Palace reset — wipes ChromaDB
Cell 3  → Batch-ingest ALL PDFs in academic_data/ into the palace
Cell 4  → console_log() helper + Tesseract path resolver (VS Code-safe logging)
Cell 5  → OCR diagnostics (verify Tesseract + Poppler are installed)
Cell 6  → Configure Granite 3.1 LLM + embedding model + Replicate client
Cell 7  → Single-document ingestion from Google Drive link(s), with OCR fallback
Cell 8  → Semantic chunking of the current document + metadata labelling
Cell 9  → MemPalace Bridge — push current-document nodes into the persistent
          ChromaDB store (UPSERT semantics, with fallback paths)
Cell 10 → Memory Stats Dashboard — summarise what's in the palace
Cell 11 → Label Index Retriever — browse/filter palace contents by wing/room/hall
Cell 12 → Load "awesome-notebookLM" style library (for slide-brief styling)
Cell 13 → Visual answer renderer + slide-brief builder/exporter
Cell 14 → Query Fusion retriever (paraphrase-and-fuse retrieval, sequential mode)
Cell 15 → Runtime preset switcher (toggles visual panel / brief / export via env vars)
Cell 16 → Bridge shim: points current_doc_index at palace_index in batch-ingest mode
Cell 17 → run_academic_query() — the core answer-routing backend function
Cell 18 → "Rich Q&A Widget UI" — full ipywidgets dashboard (screenshot-style)
Cell 19 → "Rapid Paper Q&A" — a SECOND, independent, self-contained widget UI
```

Two things are worth flagging immediately about this structure, covered in more detail in §4:

- **Cell numbering in comments doesn't match actual notebook position.** Header comments say things like `# Cell 4 —`, `# CELL 6 —`, `# Cell 17 —`, but the *physical* notebook index (0-based) is offset by one and, from Cell 17 onward, by two. This is almost certainly the result of cells being inserted/reordered during development without updating the header comments.
- **There are effectively three separate Q&A front-ends**: `ate_ui.py` (the external module discussed earlier in this conversation), Cell 18's inline "Rich Q&A Widget UI", and Cell 19's "Rapid Paper Q&A" widget. They are not the same code and don't share state cleanly (see §4).

---

## 3. Cell-by-Cell Breakdown

### Cell 0 — Dependency Installation
**Intent:** Install every package the rest of the notebook depends on in one place, and patch Jupyter's event loop so LlamaIndex's async internals don't deadlock.
**Logic:**
- `%pip install -q` a long list of packages spanning retrieval (llama-index + sub-packages), vector storage (chromadb), embeddings (sentence-transformers), the LLM client (replicate), document/OCR extraction (pytesseract, pdf2image, PyMuPDF, pdfplumber, python-docx, openpyxl), and the widget UI stack (ipywidgets, jupyterlab_widgets, widgetsnbextension).
- Applies `nest_asyncio.apply()` — required because Jupyter already runs an event loop, and LlamaIndex's async code would otherwise raise "event loop already running" errors.
- Runs light validation imports (`ipywidgets`, `pdfplumber`, `docx`, `openpyxl`) and prints ✅/⚠️ per package so a failed install is visible immediately instead of surfacing as a cryptic `NameError` several cells later.
- Prints a manual reminder that OCR needs two **external, non-pip** binaries (Tesseract OCR, Poppler) which this cell cannot install.

**Assumptions/edge cases:**
- Assumes internet access to PyPI at runtime.
- Assumes a Windows environment for the Tesseract path note (though the actual OCR code elsewhere handles other OSes too).
- Silent partial failure is possible: if one package in the long `%pip install` line fails, pip may still report success for the others; the validation block only checks four of the ~20 installed packages.

---

### Cell 1 — Memory Palace Reset (manual, guarded)
**Intent:** A deliberately dangerous "wipe everything" cell, gated behind an explicit `CONFIRM_RESET = True` flag so it's never triggered by accident on a routine "Run All".
**Logic:**
- Checks the current vector count via a throwaway ChromaDB client, distinguishing "palace has data" from "ChromaDB's Rust bindings are already dead in this kernel" (a known failure state — see §4).
- If `CONFIRM_RESET` is `False` (default), it only **reports status** — no deletion happens.
- If `True`, it performs a full teardown: deletes the ChromaDB collection, removes leftover HNSW segment folders and SQLite WAL/SHM files from disk, resets the docstore JSON to empty, and nulls out every palace-related variable (`palace_client`, `palace_index`, etc.) in `globals()`.
- Prints an explicit numbered restart checklist afterward, because — critically — **calling `_system.stop()` on ChromaDB permanently kills the Rust bindings for the rest of the kernel process**, so continuing to use the notebook without restarting will fail.

**Assumptions/edge cases:**
- Assumes `palace_client` may or may not already exist in `globals()` (handles both).
- Explicitly avoids calling `_system.stop()` in the non-confirmed branch specifically *because* that call is destructive to the whole kernel, not just the data — an important asymmetry the comments call out.
- File deletion can raise `PermissionError` if ChromaDB's SQLite files are still locked by an open connection; this is caught and surfaced as an actionable message rather than crashing.

---

### Cell 2 — Batch Ingest PDFs into Memory Palace
**Intent:** The primary bulk-ingestion path — index every PDF in `academic_data/` at once, all tagged with one fixed metadata label set (`wing=Academics`, `room=Adaptive Leadership`, `hall=Adaptive Leadership`, `drawer_type=Adv. Dip`), skipping the pre-merged `source_material.pdf`.
**Logic:**
- Detects dead ChromaDB Rust bindings up front (via `try/except (AttributeError, ValueError)`) and, if dead, prints a restart checklist instead of proceeding.
- Lazily initialises `embed_model` (HuggingFace BGE-small) and `splitter` (semantic node parser) if they aren't already in `globals()`.
- Globs `academic_data/*.pdf`, excluding the skip-list.
- For each PDF: loads it via `SimpleDirectoryReader`, stamps the fixed metadata onto every `Document`, runs it through an `IngestionPipeline` (semantic splitter → docstore → ChromaVectorStore, with `DocstoreStrategy.UPSERTS` for idempotent re-runs), and re-stamps metadata onto the resulting nodes (belt-and-braces, since the pipeline can sometimes drop custom metadata).
- **Fallback upsert:** if the pipeline ran but the palace's vector count didn't actually increase (a real observed failure mode with this pipeline/vector-store combination), it manually rebuilds the raw ChromaDB payload (`_chroma_upsert`) and upserts directly — bypassing the pipeline abstraction entirely.
- After all files: persists the docstore, rebuilds `palace_index` and `palace_query_engine` from the vector store, and prints a summary (files ingested / failed, total nodes, final vector count).

**Assumptions/edge cases:**
- Assumes `academic_data/` exists and is readable; if empty, prints a warning and exits cleanly rather than erroring.
- Per-file `try/except` means one corrupt/unreadable PDF doesn't abort the whole batch — it's recorded in `failed` and reported at the end.
- The "pipeline ran but count didn't increase" fallback is a workaround for what appears to be an intermittent bug in how the ingestion pipeline interacts with the Chroma vector store — worth knowing about if you ever refactor this cell, since removing the fallback silently could reintroduce silent data loss.
- Fixed metadata means **all** batch-ingested PDFs get identical `wing`/`room`/`hall` labels regardless of actual content — this is a coarse categorisation by design, not a bug, but it means the label-based filtering in Cell 11 won't meaningfully discriminate between batch-ingested documents.

---

### Cell 3 — Console/Logger Helper + Tesseract Resolver
**Intent:** Replace `ipywidgets`-based UI logging with plain `print()`-based logging (because ipywidgets output doesn't always render reliably inside VS Code's notebook panel), and provide a robust, cross-platform way to locate the Tesseract OCR binary without requiring the user to hardcode a path.
**Logic:**
- `console_log(msg, level='INFO')` — timestamps and prints every log line uniformly across the whole notebook.
- `resolve_tesseract_cmd()` — searches, in priority order: (1) an explicit `TESSERACT_CMD` env var, (2) `shutil.which("tesseract")` (standard PATH lookup), (3) two hardcoded Windows Program Files paths, (4) a recursive glob under WinGet's per-user package install directory (since WinGet installs into a hashed, unpredictable folder name). The first path that actually exists on disk wins; it's written back into `TESSERACT_CMD` and into `pytesseract.pytesseract.tesseract_cmd` so every downstream OCR call picks it up automatically.
- A `ConsoleHandler(logging.Handler)` class is also defined (truncated in this summary) to route Python's standard `logging` module output through the same `console_log` formatting.

**Assumptions/edge cases:**
- The WinGet glob pattern assumes the Windows WinGet package-manager install convention; on non-Windows systems the entire block is skipped via `if os.name == "nt"`.
- Silently returns `None` if Tesseract truly isn't installed anywhere — the caller (`extract_text_or_ocr` in Cell 6) is responsible for deciding that's fatal to OCR (but not to the whole notebook, since non-scanned PDFs don't need OCR at all).

---

### Cell 4 — OCR Diagnostics
**Intent:** A standalone sanity-check cell to confirm Tesseract and Poppler are both correctly installed and reachable *before* running a full ingestion that might silently fall back to no-OCR mode.

*(Cell content not fully expanded in this pass — recommend a quick manual read if you need exact diagnostic output format; the header comment confirms its scope matches this description.)*

---

### Cell 5 — Configure Granite 3.1 & Security Guardrails
**Intent:** Set up the LLM and embedding model that every retrieval/answer step downstream depends on, with an explicit "evidence-only" safety prompt baked into the model configuration itself (not just applied per-query).
**Logic:**
- Prompts for `REPLICATE_API_TOKEN` (checks env var first, falls back to interactive `input()`), and hard-stops with `ValueError` if none is provided — every downstream LLM call would fail anyway, so this fails fast with a clear message.
- Configures `llm = Replicate(...)` pointing at `ibm-granite/granite-3.1-8b-instruct`:
  - `temperature=0.1` for near-deterministic, factual output.
  - `context_window=128000` matching Granite 3.1's native limit.
  - `request_timeout=600.0` (10 minutes) to tolerate slow cold-starts on Replicate's infrastructure.
  - A `system_prompt` that explicitly forbids introducing outside knowledge, mandates admitting when evidence is missing, and requires formal academic prose.
- Loads the embedding model with a **three-tier fallback chain**: primary (`BAAI/bge-small-en-v1.5`) → secondary (`sentence-transformers/all-MiniLM-L6-v2`, more widely cached) → `MockEmbedding` (random vectors, purely to keep the pipeline from crashing when HuggingFace is completely unreachable — explicitly flagged as not useful for real retrieval).
- Registers both models globally via LlamaIndex's `Settings.llm` / `Settings.embed_model`.
- **Patches the Replicate SDK's default client** with an explicit 600-second read timeout — the comment explains this is necessary because newer `replicate` SDK versions (≥0.25) silently ignore the `request_timeout` passed to the LlamaIndex wrapper; the fix has to happen on the underlying `Client` object directly.

**Assumptions/edge cases:**
- Assumes an interactive kernel if the env var isn't set (the `input()` call will hang/fail in a fully non-interactive batch run).
- The embedding fallback chain masks HuggingFace connectivity issues by silently degrading retrieval quality (via `MockEmbedding`) rather than crashing — worth watching for if search results ever seem nonsensical, since there's no loud failure to alert you.

---

### Cell 6 — Single-Document Ingestion from Google Drive
**Intent:** An alternative to the batch-folder ingestion in Cell 2 — download one or more PDFs directly from Google Drive share links (comma-separated), for ad-hoc single-session research rather than permanent batch cataloguing.
**Logic:**
- `extract_drive_file_id()` — regex-extracts the file ID from either of Google Drive's two common share-URL formats.
- `download_pdf_from_drive()` — tries `gdown` first (handles Drive's virus-scan interstitial pages and auth cookies automatically), verifies the result is actually a PDF by checking the `%PDF-` magic-byte header, and falls back to a manual two-endpoint `requests`-based download with confirm-token extraction (from either a cookie or the HTML body) if `gdown` fails or returns a non-PDF response.
- `extract_text_or_ocr()` — tries native text extraction via PyMuPDF first; if the extracted text is suspiciously short (<50 chars after stripping), falls back to rasterising each page at 300 DPI and running Tesseract OCR, writing the result to a sidecar `.ocr.txt` file.
- Main flow: prompts interactively for one or more Drive links, downloads each with **per-link error isolation** (one bad link doesn't abort the others), and if multiple PDFs were provided, merges the successful ones into a single `source_material.pdf` (merge logic truncated in this pass, but confirmed to use PyMuPDF via `fitz.open()`).

**Assumptions/edge cases:**
- Assumes the interactive `input()` prompt is acceptable (same caveat as Cell 5).
- Google Drive sharing must be set to "Anyone with the link: Viewer" — both download paths explicitly detect `401`/`403` responses and surface this exact remediation instruction rather than a raw HTTP error.
- If **all** links fail, raises `RuntimeError` rather than silently continuing with zero documents.
- OCR fallback assumes Tesseract/Poppler are installed (per Cell 3/4) — if not, `extract_text_or_ocr` logs an error and returns the original (text-less) PDF path rather than crashing, meaning downstream ingestion would proceed with an effectively empty document.

---

### Cell 7 — Semantic Chunking + Metadata Labelling (Current Document)
**Intent:** Take whatever was ingested via Cell 6 (the single-document path) and turn it into semantically coherent chunks with hierarchy metadata, plus build a fast, lightweight, in-session query engine scoped to *just this document* — separate from the persistent Memory Palace.
**Logic:** Uses `SemanticSplitterNodeParser` (embedding-aware splitting at natural topic boundaries rather than fixed character counts) to chunk `source_file`, then attaches the same four-level metadata hierarchy used elsewhere, then builds `current_doc_index` / `current_doc_query_engine` for immediate querying without touching ChromaDB.

*(Full body truncated in this pass; header comment and downstream references in Cells 9/16/17 confirm this scope.)*

---

### Cell 8 — MemPalace Bridge (Persistent Long-Term Memory)
**Intent:** Push the current document's semantic nodes (from Cell 7) into the **persistent** ChromaDB-backed Memory Palace, so single-document research sessions also contribute permanently to the long-term corpus — with UPSERT semantics so re-running doesn't duplicate data.
**Logic:**
- Same dead-Rust-bindings guard pattern as Cells 1/2.
- Lazily re-creates `splitter` if Cell 7 was skipped.
- **Branches on whether Cell 7 actually produced `documents`:** if not (e.g. the user only ran the batch-ingest path and skipped single-doc ingestion entirely), it skips the ingestion pipeline and just reconnects `palace_index` to whatever's already in the persistent store — this is what makes Cell 16's `current_doc_index` shim necessary later.
- If documents *are* present: runs an `IngestionPipeline` with `DocstoreStrategy.UPSERTS`, re-stamps hierarchy metadata onto every resulting node (pulling from `wing_label`/`room_label`/`hall_label`/`drawer_type` globals, each with sensible defaults if unset), persists the docstore, and — using the same before/after vector-count comparison pattern as Cell 2 — applies **two separate fallback upsert paths** (`_build_chroma_payload`) if the pipeline silently failed to write vectors: one using the pipeline's own output nodes, another (last resort) using raw `nodes` from Cell 7 if the pipeline produced *nothing at all*.
- Rebuilds `palace_index` / `palace_query_engine` at the end regardless of which path was taken, and logs a detailed before/after/final vector-count trace for debugging.

**Assumptions/edge cases:**
- This cell is explicitly designed to work correctly **whether or not** the single-document ingestion path (Cells 6–7) was actually run — a deliberate defensive design given the notebook supports two independent ingestion workflows that can be mixed.
- The two-tier fallback (pipeline-nodes vs. bootstrap-step4-nodes) suggests the underlying pipeline→vector-store write path has been unreliable enough in practice to warrant two independent safety nets — worth being aware of if extending this logic, since a naive refactor could silently remove real protection against data loss.

---

### Cell 9 — Memory Stats Dashboard
**Intent:** A read-only reporting cell — summarise what's actually stored in the Memory Palace so you can sanity-check ingestion results without writing ad-hoc ChromaDB queries by hand.
**Logic:**
- Guards on `palace_collection` existing (prints a restart checklist if not — same dead-bindings failure mode as elsewhere).
- Scans up to `PALACE_DASHBOARD_MAX_SCAN` (env-configurable, default 1500) metadata records via `collection.get(limit=..., include=["metadatas"])`, rather than scanning the entire collection unconditionally — a deliberate performance cap for large palaces.
- Uses `collections.Counter` to tally distribution across each of the four metadata levels (`wing`, `room`, `hall`, `drawer_type`), printing the top values for each.
- Also calls `collection.peek()` to show a handful of raw sample records for spot-checking.

**Assumptions/edge cases:**
- If `palace_count > scan_limit`, explicitly tells the user the dashboard is showing a partial view and how to see more (raise the env var) — avoids silently misleading statistics on a large palace.
- All `Counter` calls default missing metadata fields to the same defaults used during ingestion (`"Projects"`, `"General_Topic"`, etc.), so older or malformed records without full metadata still get counted sensibly rather than crashing.

---

### Cell 10 — Label Index Retriever
**Intent:** Give the user two exploratory tools: one to see the full catalogue of unique wing/room/hall combinations actually present in the palace, and one to fetch chunks filtered by any subset of that hierarchy (optionally combined with a semantic similarity query on top).
**Logic:**
- `get_label_index(collection, max_scan=5000)` — scans metadata (capped, same pattern as Cell 9) and aggregates into a `defaultdict(set)` keyed by `(wing, room, hall)` tuples, where each value is the set of file names living at that address. Returns an empty dict (with a warning) if the palace is empty.
- `retrieve_by_label(...)` — (signature/body truncated in this pass) filters by label combination and optionally layers semantic search on top, based on the function name and surrounding context.

**Assumptions/edge cases:**
- `max_scan=5000` is a separate, independently-configured cap from Cell 9's dashboard cap — on a very large palace (>5000 chunks), this index will be incomplete without manually raising the parameter.

---

### Cell 11 — Load "awesome-notebookLM" Style Library
**Intent:** Parse a local style-guide document (likely a README from a vendored/forked "awesome-notebookLM" resource) into a lookup dict of named style prompts, used later to flavor auto-generated slide briefs (e.g. an "artifact" style, per Cell 13's default).
**Logic:** Helper functions `_normalize_heading`, `_extract_style_blocks`, `_pick_style`, and the main `load_notebooklm_style_library(readme_path)` — parses markdown headings and their following content blocks into a dict, presumably keyed by normalized heading text.

*(Body truncated in this pass; downstream usage in Cell 13 confirms the shape: `style_library['curated'][style_key]` → a prompt string.)*

**Assumptions/edge cases:** Assumes the referenced README file exists at a fixed local path and is well-formed markdown with heading-delimited style blocks; a missing or malformed file would likely degrade `style_library` to an empty/partial dict rather than crash, based on the defensive `.get(style_key, "")` pattern seen in Cell 13.

---

### Cell 12 — Visual Answer Renderer + Slide Brief Export
**Intent:** Three presentation-layer helpers used by the research loop to turn a raw `run_academic_query()` result into (a) a nicely styled HTML panel shown inline in the notebook, and (b) an optional structured JSON "brief" suitable for feeding into an external slide-generation tool.
**Logic:**
- `render_answer_panel(question, result, max_sources=8)` — builds an HTML card (via inline CSS, since VS Code's notebook renderer doesn't reliably load external stylesheets) showing the question, retrieval mode, the answer text, and a numbered source list (each with file name + wing/room/hall/drawer metadata + a text snippet). Uses `.format()` rather than an f-string for the per-source HTML fragment specifically because the HTML itself contains literal curly braces that would otherwise confuse an f-string parser. Displays via `IPython.display.display(HTML(...))` — explicitly **not** `print()`, since printing would show raw tags instead of rendering them.
- `build_slide_brief(question, result, style_key="artifact")` — packages the question, answer, retrieval mode, a chosen style prompt (looked up from Cell 11's style library, falling back to an empty string if the key doesn't exist), and up to 10 compact source summaries into a plain JSON-serialisable dict. Also embeds a fixed `instructions` list telling any downstream slide tool to use only the provided sources, keep one claim per slide, preserve citation traceability, and avoid unsupported synthesis — i.e., the same evidence-only discipline enforced at the LLM level is re-asserted here for whatever consumes this JSON next.
- `export_slide_brief(brief, output_dir="academic_data/visual_briefs")` — writes the brief to a timestamped JSON file (`slide_brief_YYYYMMDD_HHMMSS.json`), creating the output directory if needed, with `ensure_ascii=False` to preserve accented characters and `indent=2` for human readability.

**Assumptions/edge cases:**
- `render_answer_panel` truncates `sources` to `max_sources` *before* building HTML, so a result with more sources than that will silently show only the first N — reasonable for readability, but worth knowing if you ever need a complete source audit trail.
- Timestamp-based filenames in `export_slide_brief` mean two exports within the same second would theoretically collide — a low-probability edge case given this is triggered by manual Q&A turns, not a tight loop.

---

### Cell 13 — Advanced Query Fusion (Sequential Stability Mode)
**Intent:** Load a **local, forked copy** of LlamaIndex's `QueryRewritingRetrieverPack` (rather than the pip-installed upstream version), which rewrites a question into paraphrased variants and fuses retrieval results across them for better recall than a single-pass query.
**Logic:**
- Inserts `query_rewriting_pack/` (a local folder in the workspace) at the front of `sys.path` so imports resolve to the local fork first.
- Tries a normal namespace import first; if that fails (e.g. because the local package's `__init__.py` chain is broken, or there's a naming collision with the pip-installed version), falls back to loading the module directly from its file path via `importlib.util.spec_from_file_location` — bypassing Python's normal import resolution entirely.
- Instantiates the pack against `nodes` (from Cell 7 — i.e., this is scoped to the **current document**, not the full palace) with `chunk_size=256`, `vector_similarity_top_k=5`, and — critically — `num_queries=1`.
- The comments are explicit that `num_queries=1` is a deliberate stability trade-off: running multiple query variants in parallel risks async event-loop conflicts inside a Jupyter kernel, so this cell sacrifices the "fusion" part of query fusion (no actual multi-query paraphrase-and-merge happens with `num_queries=1`) in favor of not crashing. The comment notes this can be increased once concurrency is confirmed safe.

**Assumptions/edge cases:**
- Depends on `nodes` existing in `globals()` from Cell 7 — if the batch-ingest-only path was used instead, this cell would fail with a `NameError` unless `nodes` was populated some other way.
- With `num_queries=1`, this cell currently provides **no fusion benefit over a plain retriever** — it's effectively a single-query retriever wrapped in fusion-pack machinery, present for future use once the concurrency issue is resolved.

---

### Cell 14 — Runtime Visual Preset Switcher
**Intent:** A single-variable control panel (`ATE_PRESET`) that lets the user pick one of three named feature bundles for the research loop, without having to remember and hand-set four separate environment variables individually.
**Logic:**
- `PRESETS` dict maps `'visual_only'` / `'visual_brief'` / `'visual_brief_export'` to explicit `{env_var: "1"|"0"}` mappings for `ATE_VISUAL_PANEL`, `ATE_AUTO_BRIEF`, `ATE_AUTO_BRIEF_EXPORT`.
- Validates `ATE_PRESET` against the known keys, raising `ValueError` immediately on a typo rather than silently doing nothing.
- Writes **all four** variables explicitly every time (rather than only writing what's different from defaults) — the comment notes this is intentional, so a stale value left over from a previous kernel session's different preset can't leak through.
- `ATE_BRIEF_STYLE` is set via `os.environ.setdefault(...)` instead — the one exception, so that an explicit override (e.g. from a `.env` file or an earlier manual cell) is preserved rather than clobbered.
- Prints a confirmation summary of all four resulting values.

**Assumptions/edge cases:** This cell only writes environment variables; it has no effect unless the research-loop cell (Cell 17/18/19, depending on which is used) actually reads `ATE_VISUAL_PANEL` / `ATE_AUTO_BRIEF` / `ATE_AUTO_BRIEF_EXPORT` / `ATE_BRIEF_STYLE` at call time.

---

### Cell 15 — Bridge: `current_doc_index` Fallback for Batch-Ingest Mode
*(Discussed in detail in the previous turn of this conversation.)*
**Intent:** Ensure `current_doc_index` — a variable Cell 16/17 expects for "local document" retrieval — is always defined, even if the user only ran the batch-ingest path (Cell 2) and never populated it via the single-document flow (Cells 6–7).
**Logic:** If `current_doc_index` is missing or `None`, points it at `palace_index` (since in batch mode, every PDF is already in the palace, so scoping to "the palace" and scoping to "the current doc" become equivalent — every query naturally gets full cross-document coverage). Otherwise, leaves an already-set single-doc index alone.

---

### Cell 16 — Backend Query Bridge (`run_academic_query`)
**Intent:** The single, central function that both widget UIs (Cell 18 and Cell 19) actually call to get an answer — abstracting away *which* query engine is available so the frontend doesn't need to know about single-doc vs. Memory Palace vs. fusion retrieval.
**Logic:**
- `_prepare_sources(nodes, max_sources=8)` — normalises a list of retrieved nodes into the flat dict shape (`file_name`, `wing`, `room`, `hall`, `drawer_type`, `snippet`, `retriever`) used by every downstream panel/brief renderer. Snippets are whitespace-collapsed and truncated to 220 characters.
- `_resolve_query_engine()` — tries, in priority order: `current_doc_query_engine` → `palace_query_engine` → (if only `palace_index` exists) constructs a query engine from it on the fly. Raises a clear `RuntimeError` with remediation instructions if none of the three are available.
- `_retrieve_nodes(engine, question, top_k=8)` — defensively obtains a retriever from whatever engine object was resolved (tries `.as_retriever()` first, falls back to using the engine directly if it already exposes `.retrieve()`), swallowing exceptions and returning an empty list rather than propagating — retrieval failure degrades to "no sources shown," not a crash.
- `run_academic_query(question, max_attempts=3)` — validates the question is non-empty, resolves an engine, and **retries the actual LLM query up to `max_attempts` times** before giving up (useful for transient Replicate cold-start/timeout failures). On success, also retrieves supporting nodes for the source panel — falling back to the Cell 13 query-fusion pack if the primary engine's retriever returned nothing. Returns the standard `{answer, sources, retrieval_mode}` dict shape used everywhere else in the notebook.

**Assumptions/edge cases:**
- The retry loop only retries the **query call**, not engine resolution — if `_resolve_query_engine()` itself fails, that's a hard failure with no retry.
- If the resolved engine's `.query()` call succeeds but returns an empty string, the function still reports it as a (falsy) answer and falls through to `"No answer returned from the available query engine."` — an explicit empty-answer safeguard so the UI never shows a blank response with no explanation.

---

### Cell 17 — "Rich Q&A Widget UI" (inline, screenshot-style)
**Intent:** A full `ipywidgets`-based chat interface built directly inside the notebook — this appears to be the **original source** that `ate_ui.py` was later extracted/exported from (the two share near-identical structure: textarea, file upload, History/Clear/End/Research buttons, and a right-hand "Live Source Overview" / "Status Monitor" panel).
**Logic (high level, since the full 180-line body mirrors what was already documented for `ate_ui.py` earlier in this conversation):**
- Defines fallback stub versions of `_detect_prompt_mode`, `_append_exchange`, `_extract_attachment_text`, and `run_academic_query` **only if they don't already exist** — so this cell can run standalone even before the backend cells, showing a "UI is ready but backend isn't" message instead of crashing.
- Builds the same widget set as `ate_ui.py`: `_qa_text` (Textarea), `_qa_upload` (FileUpload), History/Clear/End/Research buttons, a status `HTML` widget, and two `Output` widgets (main answer area + side panel).
- `_get_upload_files()` — normalises `ipywidgets.FileUpload`'s value across different ipywidgets versions (older versions return a dict keyed by filename; newer versions return a list of dicts) into a single consistent `list[tuple[name, bytes]]`.
- `_qa_build_side_html()` — builds the "Live Source Overview" panel HTML from whatever's in `PDF_SOURCES` and `palace_collection.count()`, with a **hardcoded placeholder fallback** (fake "Nature Journal" / "PubMed Central" / "Google Scholar" entries) shown if no real sources are available yet — presumably for demo/screenshot purposes when the palace is empty.

**Assumptions/edge cases:**
- Since this cell defines its own copies of `_qa_build_side_html`, `_qa_refresh_side`, `run_academic_query`, etc., directly in the notebook's global namespace, running **both** this cell and Cell 15 (`build_ui(globals())` from `ate_ui.py`) in the same session means whichever runs *last* wins — their function names collide. This is the same class of bug already fixed in `ate_ui.py` in this conversation (the `ns` name), and if this inline cell is still in active use, it's worth checking whether it has the equivalent fix or not, since it appears to be an earlier, un-synced copy of the same code.

---

### Cell 18 — "Rapid Paper Q&A" (independent, second widget UI)
**Intent:** A **completely separate**, self-contained Q&A widget — explicitly designed for a lighter-weight, ephemeral, no-ChromaDB workflow: paste/upload PDFs directly into this cell's own widget panel, get an in-memory-only index (no persistence to the Memory Palace at all), and ask questions with prefix-based answer-mode selection (`!short`, `!long`, `!summarise`, `!bullet`, `!compare`, `!define`, `!critique`) or slash-style commands (`help`, `history`, `clear`, `end`).
**Logic:**
- Explicitly reuses `REPLICATE_API_TOKEN`, `embed_model`, and `splitter` from the main engine setup (Cells 5/2), but hard-stops with `RuntimeError` if the token isn't available — same fail-fast pattern as Cell 5.
- Maintains its own isolated mutable state in a single `_pr_state` dict (`nodes`, `retriever`, `labels`, `history`, `ctx_mem`, `q_num`) — the comment notes this is deliberate: "closures need a container, not bare variables," i.e. nested widget-callback functions can mutate a dict's contents but can't rebind an outer bare variable without `nonlocal`, so a shared mutable container sidesteps that Python closure limitation.
- A large family of `_pr_*`-prefixed helpers: Drive download/detection (`_pr_is_gdrive`, `_pr_file_id`, `_pr_download_gdrive`), text extraction (`_pr_extract_text`), answer-mode parsing (`_pr_detect_mode`, `_pr_mode_label`), a **verbatim-copying detector** (`_pr_verbatim_check`, using n-gram overlap with configurable warn/alert thresholds — `PR_VERBATIM_WARN=0.05`, `PR_VERBATIM_ALERT=0.15` — presumably to flag when the model's "answer" is suspiciously close to just copying source text rather than synthesising), the actual Granite call (`_pr_granite`), network-error classification (`_pr_network_err`), and several HTML renderers (`_pr_render`, `_pr_render_history`, `_pr_render_help`).
- Widget event handlers (`_pr_on_load`, `_pr2_on_clear`, `_pr2_show_history`, `_pr2_on_end`, `_pr2_on_submit`) wire the whole thing together.

**Assumptions/edge cases:**
- This is a genuinely independent Q&A system, not a variant of the other two — it has its own PDF ingestion (in-memory, ephemeral, no Chroma), its own retriever, its own history, and its own answer-mode system. Running this cell does **not** interact with `palace_index`, `current_doc_index`, or `run_academic_query` at all except reusing shared setup variables.
- Per-source config block at the top (`PR_TOP_K`, `PR_MAX_TOKENS` per mode, `PR_TEMPERATURE=0.15`, `PR_HISTORY_CTX=3`) is self-contained and doesn't affect any other cell.
- The verbatim-check thresholds (5% warn / 15% alert n-gram overlap) are a heuristic, not a hard block — worth confirming whether high-overlap answers are actually surfaced differently to the user or just logged, if academic-integrity guarantees matter for this tool's use case.

---

## 4. Cross-Cutting Assumptions & Notable Edge Cases

**a) The ChromaDB "dead Rust bindings" failure mode.**
This is the single most-repeated defensive pattern in the notebook (appearing in Cells 1, 2, 8, 9, 10). The root cause, per the comments: calling a ChromaDB client's `_system.stop()` — which happens deliberately in the confirmed reset path of Cell 1 — permanently invalidates the shared Rust DLL bindings **for the entire kernel process**, not just for that one client object. Every cell that touches ChromaDB therefore checks for this state (`AttributeError: 'RustBindingsAPI' object has no attribute 'bindings'` or `ValueError: Could not connect to tenant default_tenant`) up front and prints an explicit "restart the kernel, then re-run cells X, Y, Z in this order" checklist rather than letting a confusing low-level exception surface. If you ever touch this logic, preserve the check — it's the difference between a clear message and a genuinely confusing crash several cells later.

**b) Two independent ingestion paths that can be mixed or skipped.**
The notebook supports both a bulk batch-folder ingest (Cell 2) and a single-document Drive-link ingest (Cells 6–7), and several later cells (8, 15, 16) explicitly handle the case where only one of the two was run. This is good defensive design, but it does mean state like `current_doc_index`, `nodes`, and `documents` may or may not exist depending on which workflow the user actually followed in a given session — any new cell added to this notebook should follow the same `"x" not in globals()` guard pattern already used throughout rather than assuming a fixed cell-execution order.

**c) Cell-numbering drift.**
In-cell header comments (`# Cell N —`) do not match physical notebook position from partway through the notebook onward (confirmed via `grep`: e.g. the physical 16th code cell is headed "Cell 17", and the physical 18th is headed "Cell 19"). This strongly suggests cells were reordered or inserted during iterative development without updating every header. Not a functional bug, but worth fixing if you want the in-notebook documentation to be trustworthy for onboarding someone else — currently, following the header comments' stated cell numbers to navigate would lead to the wrong physical cell.

**d) Three separate, only loosely-related Q&A UIs.**
`ate_ui.py` (external module), Cell 17's inline "Rich Q&A Widget UI", and Cell 18's "Rapid Paper Q&A" are three distinct implementations. The first two appear to be near-duplicates of each other (one likely exported from the other), sharing the same widget layout, the same `_qa_*` function names, and — importantly — the same `ns`-not-defined class of bug that was diagnosed and fixed in `ate_ui.py` earlier in this conversation. **That fix has not been verified against Cell 17's inline copy** — if Cell 17 is still actively used (rather than superseded by importing `ate_ui.py`), it likely has the identical bug and would benefit from the same fix. Cell 18 is architecturally independent and doesn't share this risk.

**e) Interactive `input()` calls.**
Cells 5 (Replicate token) and 6 (Drive links) both use blocking `input()` calls as a fallback when the relevant environment variable isn't pre-set. This makes the notebook interactive-only for those cells — running it as a scheduled/non-interactive batch job would require pre-populating `REPLICATE_API_TOKEN` and reworking Cell 6's link-collection to not depend on stdin.

**f) Retry and fallback logic is pervasive but not uniform.**
Ingestion pipelines get "pipeline ran but count didn't increase" fallback upserts (Cells 2, 8); LLM queries get a 3-attempt retry (Cell 16); embedding model loading gets a 3-tier fallback chain (Cell 5); Drive downloads get a 2-method fallback (Cell 6). Each of these is a reasonable, independently-justified defensive measure given the specific failure modes observed with each underlying library — but it does mean debugging "why didn't X happen" in this notebook often requires checking which specific fallback tier actually fired, since failures are designed to degrade gracefully rather than surface loudly. The `console_log()` calls at each fallback tier are the main way to see which path was actually taken — worth grepping the log output for `WARN`/`ERROR` lines first when something seems off.
