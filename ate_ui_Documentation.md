# `ate_ui.py` — Documentation

## 1. High-Level Purpose

`ate_ui.py` builds and injects a complete `ipywidgets`-based chat interface for the Academic Truth Engine notebook — a styled, screenshot-quality dashboard with a research question box, file attachments, a live source panel, and session history — directly into the calling notebook's global namespace.

It does this via an unusual but deliberate pattern: rather than defining the widgets as normal Python functions in this module, the entire UI (widgets, callbacks, and CSS) is written as one large string of Python/HTML source and `exec()`'d inside the notebook's own `globals()` dict. That's what lets the UI's callback functions freely read notebook-level variables like `PDF_SOURCES`, `palace_collection`, and `run_academic_query` — they aren't imported or passed in explicitly; they're looked up live, by name, in the shared namespace at the moment each button is clicked.

The single public entry point is `build_ui(ns: dict)`, called from the notebook as `build_ui(globals())`.

---

## 2. Step-by-Step Logic Breakdown

### 2.1 The `build_ui(ns)` wrapper (lines 1–4, 661–665)
- Takes one argument, `ns` — the dict to use as the execution namespace. In practice this is always the caller's `globals()`.
- Line 664, `ns['ns'] = ns`, inserts the namespace dict into itself under the key `'ns'`. This is the fix applied earlier in this conversation: `exec(code, ns)` only gives the executed code access to whatever is *in* `ns` as globals — it does not give it a Python closure over `build_ui`'s local `ns` parameter. Since every callback inside `code` refers to a bare name `ns` (e.g. `ns.get('PDF_SOURCES', ...)`), that name has to actually exist as a key in the dict for those lookups to resolve at call time.
- Line 665, `exec(code, ns)`, compiles and runs the entire `code` string using `ns` as both globals and locals. Every widget, function, and variable the string defines ends up living directly in the notebook's own namespace — that's what makes them visible/persistent as normal notebook globals after `build_ui()` returns.

### 2.2 The `code` string itself (lines 5–659)
This is a raw string (`code = r'''...'''` — note the `r` prefix, required so that literal backslash sequences like `\n` inside the embedded source reach `exec()` unprocessed rather than being collapsed by Python's own string-literal parsing before `exec` ever sees them). Its contents fall into five logical sections:

**a) Imports and widget construction (lines 6–58)**
Imports `ipywidgets` and the relevant `IPython.display` functions under private aliases (`_widgets`, `_ate_disp`, `_ate_HTML`, `_ate_clear`) to avoid clobbering anything the notebook may already have bound to `display`, `HTML`, etc. Then constructs the core widget set:
- `_qa_text` — the main `Textarea` for the research question, styled via a custom CSS class (`ate-research-input`).
- `_qa_upload` — a `FileUpload` widget accepting PDF/DOCX/XLSX/image formats, multi-file.
- `_qa_history_btn`, `_qa_clear_btn`, `_qa_end_btn`, `_qa_submit_btn` — the four action buttons.
- `_qa_status` — an `HTML` widget used as a live status line.
- `_qa_output`, `_qa_side` — two `Output` widgets: the main answer area and the right-hand info panel, respectively.

**b) Helper functions (lines 61–190)**
- `_get_upload_files()` — normalises `ipywidgets.FileUpload.value` into a consistent `list[(filename, bytes)]`. This exists because the `FileUpload` widget's `.value` shape has changed across `ipywidgets` versions: older versions return a `dict` keyed by filename, newer versions return a `list` of per-file dicts. The function checks both shapes so the rest of the code doesn't need to know which version is installed.
- `_qa_build_side_html()` — builds the HTML for the right-hand "Live Source Overview" / "Status Monitor" panel. Pulls `PDF_SOURCES` (a list of file paths, deduplicated by basename, capped at 5) and `palace_collection.count()` (the current vector count) out of `ns`, formats them into source rows, and renders three cosmetic "status bar" gauges (`Source Coverage`, `Citations Found`, `Contradictions`) using a simple block-character progress-bar generator (`_bar()`).
- `_qa_refresh_side()` — clears and re-renders `_qa_side` by calling `_qa_build_side_html()`. This is the function whose call, at line 602 (module-load time) and again at the end of every successful `_on_submit()`, was throwing the `NameError: name 'ns' is not defined` before the fix.
- `_qa_set_status(msg, colour)` — updates the `_qa_status` widget's HTML value with a coloured message.
- `_qa_clear_upload()` — resets the upload widget's value and description back to empty, with a nested `try/except` fallback (tries the tuple-based reset first, since newer ipywidgets expects `()`; falls back to `{}` for older versions that expect a dict).

**c) Button callbacks (lines 193–353)**
- `_on_clear()` — wipes the text box, clears attachments, resets status, clears the output panel.
- `_show_history()` — reads `_session_data['exchanges']` from `ns` and renders each past Q&A exchange as a formatted HTML block (question, timestamp, truncated answer snippet) into `_qa_output`.
- `_on_end()` — disables all four buttons, sets a red "closed" status message, and prints a farewell line into the output panel. This is a soft/visual close — it does not tear down any Python objects or state.
- `_on_submit()` — the main event handler, triggered by the Research button:
  1. Reads the question text and any uploaded files.
  2. For each uploaded file, calls `_extract_attachment_text` (looked up from `ns`) to convert file bytes into text, catching and reporting per-file extraction errors individually rather than aborting the whole submission.
  3. Concatenates the question and any attachment text into `full_question`; if both are empty, shows a warning status and returns early without calling the backend.
  4. Calls `_detect_prompt_mode` (from `ns`) to classify the question (e.g. essay/chat/summarise), purely for the status-line display.
  5. Disables the submit button, updates status to "retrieval running…", then calls `run_academic_query` (from `ns`, with a safe no-op default if it isn't defined yet) with `max_attempts=3`.
  6. Logs the exchange via `_append_exchange` (from `ns`), if that function exists.
  7. Renders the result: if `VISUAL_PANEL_ON` is truthy in `ns` and `render_answer_panel` exists there, delegates rendering to that function (wrapped in its own `try/except` so a rendering bug doesn't take down the whole submit handler); otherwise falls back to a plain-text answer + sources dump, capped at `SOURCE_PRINT_LIMIT` entries.
  8. In a `finally` block, always re-enables the submit button and clears the upload widget — regardless of whether the query succeeded or raised.
  9. The whole backend-call section is wrapped in one outer `try/except Exception as submit_err`, so any failure anywhere in steps 5–7 is caught, printed into the output panel, and reflected in the status line as an error rather than propagating and breaking the widget UI.

**d) CSS block (lines 363–597)**
A single `<style>` block covering the whole shell (`.ate-shell`), header, two-column grid layout, cards, source rows, status bars, chips, history rows, and the themed textarea/button styling (gold/blue on near-black, matching the "Research Engine" branding visible in the screenshots earlier in this conversation).

**e) Layout assembly (lines 601–658)**
Builds the actual widget tree using `HBox`/`VBox` nesting: a left column (controls, textarea, mode-chip info bar, submit row) and a right column (header + side panel), combined into a two-thirds/one-third grid, wrapped in an outer `VBox` with the output panel below, tagged with the `ate-shell` CSS class, and finally displayed via `_ate_disp(_outer)`. Callback wiring (`.on_click(...)`) happens just before the CSS block, at lines 357–360.

---

## 3. Assumptions and Edge Cases

**a) Everything hinges on the caller passing the real notebook `globals()`.**
`build_ui` assumes `ns` is a live, mutable reference to the caller's actual global namespace — not a copy. Because `exec(code, ns)` defines every widget and function *inside* `ns`, if a copy were passed instead, none of those objects (`_qa_text`, `run_academic_query` lookups, etc.) would be reachable from the notebook afterward. This is also why re-importing/reloading this module mid-session requires `importlib.reload()` (plain `import` is a no-op once the module is already cached) — a real operational gotcha, extensively worked through earlier in this conversation.

**b) Nine external names are expected to already exist in `ns` — none are hard requirements at `build_ui()` call time, but most are needed for real functionality:**
- `PDF_SOURCES`, `palace_collection` — read defensively via `ns.get(...)`/`in ns` checks; missing values degrade to empty/zero rather than erroring.
- `run_academic_query` — has an inline lambda default (`{'answer': '', 'sources': [], 'retrieval_mode': 'local'}`) if absent, so the UI itself won't crash, but submitting a question will silently do nothing useful.
- `_extract_attachment_text`, `_detect_prompt_mode`, `_append_exchange` — looked up via `.get(...)`, guarded with `callable(...)` checks before use; if absent, attachments/mode-detection/history-logging are silently skipped rather than raising.
- `_session_data` — read via `(ns.get('_session_data') or {})`, so a missing session dict just shows "no exchanges" rather than erroring.
- `VISUAL_PANEL_ON`, `render_answer_panel`, `RUNTIME_MODE`, `SOURCE_PRINT_LIMIT` — all read with `.get(...)` and sensible fallbacks (plain-text rendering, empty depth label, a default print limit).

This defensive `.get()`-everywhere pattern means `build_ui(globals())` can safely be called *before* the backend cells (query engine, retrieval, LLM setup) have run — the UI will render and be interactive, just non-functional for actual research until those globals are populated. That's an intentional design choice (confirmed by the near-identical fallback stubs seen in the notebook's own inline copy of this UI), not an oversight.

**c) The raw-string / `exec()` architecture is fragile to naive editing.**
Because the entire UI is one big string rather than normal module-level code, any edit that introduces a `'''` sequence matching the outer string's own delimiter (as happened twice, at the CSS block and the mode-chips HTML block, before the earlier fix) will silently truncate the string and turn the rest of the file into invalid top-level Python — a failure mode that surfaces as a confusing `SyntaxError` pointing at CSS/HTML content rather than at the real cause. Similarly, any *unescaped* backslash sequence added to the string only stays literal because the outer string is raw (`r'''`); if a future edit changes that back to a plain `'''` string, escape sequences like `\n` and `\\` throughout the embedded code would silently corrupt the executed source without any Syntax-level warning at import time — the failure would only appear later, when a specific line is actually executed.

**b) `FileUpload.value` shape.**
`_get_upload_files()` explicitly handles two different `ipywidgets` versions' data shapes. If a future `ipywidgets` release changes this shape again, this function is the single place that would need updating — everything downstream (`_on_submit`) already consumes the normalised `list[(name, bytes)]` form and wouldn't need to change.

**c) Silent degradation over hard failure, by design.**
Nearly every external lookup and rendering step in this file (attachment extraction, mode detection, history append, visual-panel rendering, source formatting) is wrapped in its own narrow `try/except`, so a failure in any one of them degrades gracefully (a warning printed inline, or a feature simply not activating) rather than crashing the whole widget. The one place this pattern is *not* applied is the outer `try/except Exception as submit_err` around the entire backend call in `_on_submit` — that one is intentionally broad, since a genuine backend failure (e.g. the LLM call itself failing after all retries) should be visibly reported to the user as an error status, not silently swallowed.

**d) No teardown on "End".**
`_on_end()` disables buttons and shows a "closed" message, but doesn't release any resources, cancel any in-flight request, or prevent `build_ui()` from being called again to spin up a fresh instance. If a query is still running when "End" is clicked, it will still complete and attempt to update the (now-disabled) UI — worth confirming this doesn't throw depending on how `ipywidgets` handles output-widget writes after the request that triggered them.
