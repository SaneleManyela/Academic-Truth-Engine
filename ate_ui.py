def build_ui(ns: dict):
    """Inject the rich Q&A UI into the provided namespace by executing
    the UI source inside that namespace (so it can access notebook globals).
    """
    code = r'''# ── Rich Q&A widget UI ────────────────────────────────────────────
import ipywidgets as _widgets
from IPython.display import display as _ate_disp, HTML as _ate_HTML, clear_output as _ate_clear
import time

# ── Main input widgets ─────────────────────────────────────────────
_qa_text = _widgets.Textarea(
    placeholder=(
        "Start typing your research inquiry or topic here for real-time analysis...\n"
        "Use natural language. Paste direct text for summarization.\n\n"
        "Type your research question here...\n"
        "For summarise / paraphrase modes, paste your text directly."
    ),
    layout=_widgets.Layout(
        width="100%",
        height="390px",
        min_height="320px",
    ),
)
_qa_text.add_class("ate-research-input")

_qa_upload = _widgets.FileUpload(
    accept=".pdf,.docx,.xlsx,.jpeg,.gif,.jpg,.png,.bmp,.svg",
    multiple=True,
    description="📎 Attach (0)",
    layout=_widgets.Layout(width="150px", height="42px"),
)

_qa_history_btn = _widgets.Button(
    description="📜 History",
    layout=_widgets.Layout(width="120px", height="42px"),
)

_qa_clear_btn = _widgets.Button(
    description="✕ Clear",
    layout=_widgets.Layout(width="100px", height="42px"),
)

_qa_end_btn = _widgets.Button(
    description="○ End",
    layout=_widgets.Layout(width="95px", height="42px"),
)

_qa_submit_btn = _widgets.Button(
    description="🔍 Research",
    layout=_widgets.Layout(width="180px", height="48px"),
)

_qa_status = _widgets.HTML(
    value="<span style='color:#d8d8d8;font-size:14px;'>Ready — enter a question or attach a file.</span>"
)

_qa_output = _widgets.Output()
_qa_side = _widgets.Output()


# ── Upload helper ─────────────────────────────────────────────────
def _get_upload_files() -> list[tuple[str, bytes]]:
    val = _qa_upload.value
    files: list[tuple[str, bytes]] = []

    if isinstance(val, (list, tuple)):
        for item in val:
            if isinstance(item, dict):
                files.append((item.get("name", "file"), bytes(item.get("content", b""))))

    elif isinstance(val, dict):
        for fname, fdata in val.items():
            files.append((fname, bytes(fdata.get("content", b""))))

    return files


# ── Side panel HTML ────────────────────────────────────────────────
def _qa_build_side_html() -> str:
    src_rows = ""
    seen = set()

    pdf_list = [s for s in (ns.get('PDF_SOURCES', []) if ns is not None else []) if s]

    for p in pdf_list[:5]:
        short = str(p).replace("\\", "/").split("/")[-1]

        if short in seen:
            continue

        seen.add(short)

        src_rows += f"""
        <div class="ate-source-row">
            <span class="ate-source-icon">📄</span>
            <span>
                <strong>{short[:38]}</strong><br>
                <span class="ate-source-sub">Linked (Deep Synthesis)</span>
            </span>
        </div>
        """

    pal_count = 0

    try:
        if 'palace_collection' in ns and ns.get('palace_collection') is not None:
            pal_coll = ns.get('palace_collection')
            try:
                pal_count = pal_coll.count()
            except Exception:
                pal_count = 0
    except Exception:
        pal_count = 0

    if pal_count:
        src_rows += f"""
        <div class="ate-source-row">
            <span class="ate-source-icon">🌐</span>
            <span>
                <strong>Memory Palace ({pal_count:,} vectors)</strong><br>
                <span class="ate-source-ready">Ready for Query</span>
            </span>
        </div>
        """

    if not src_rows:
        src_rows = """
        <div class="ate-muted">(no sources loaded)</div>
        """

    def _bar(filled: int, total: int = 8) -> str:
        filled = max(0, min(filled, total))
        return "█" * filled + "░" * (total - filled)

    cov_fill = min(8, int((pal_count / 3000) * 8)) if pal_count else 2
    cit_fill = min(8, len(pdf_list) * 2)
    cov_label = "(low, build required)" if cov_fill < 3 else "(good coverage)"

    return f"""
    <div class="ate-right-stack">
        <div class="ate-card">
            <div class="ate-card-title">Live Source Overview</div>
            {src_rows}
        </div>

        <div class="ate-card">
            <div class="ate-card-title">Status Monitor</div>

            <div class="ate-status-line">
                Source Coverage <span class="ate-gold">[{_bar(cov_fill)}]</span>
            </div>
            <div class="ate-status-sub">{cov_label}</div>

            <div class="ate-status-line">
                Citations Found&nbsp;&nbsp; <span class="ate-gold">[{_bar(cit_fill)}]</span>
            </div>
            <div class="ate-status-sub">&nbsp;</div>

            <div class="ate-status-line">
                Contradictions&nbsp;&nbsp;&nbsp; <span class="ate-gold">[{_bar(1)}]</span>
            </div>
        </div>
    </div>
    """


def _qa_refresh_side() -> None:
    with _qa_side:
        _ate_clear(wait=True)
        _ate_disp(_ate_HTML(_qa_build_side_html()))


# ── Status helper ─────────────────────────────────────────────────
def _qa_set_status(msg: str, colour: str = "#d8d8d8") -> None:
    _qa_status.value = f"""
    <span style='color:{colour};font-size:14px;font-family:Segoe UI,Arial,sans-serif;'>
        {msg}
    </span>
    """


def _qa_clear_upload() -> None:
    try:
        _qa_upload.value = ()
        _qa_upload.description = "📎 Attach (0)"
    except Exception:
        try:
            _qa_upload.value = {}
        except Exception:
            pass


# ── Button callbacks ─────────────────────────────────────────────
def _on_clear(_b=None) -> None:
    _qa_text.value = ""
    _qa_clear_upload()
    _qa_set_status("Ready — enter a question or attach a file.")
    with _qa_output:
        _ate_clear(wait=True)


def _show_history(_b=None) -> None:
    exs = (ns.get('_session_data') or {}).get('exchanges', [])
    sid = (ns.get('_session_data') or {}).get('session_id', "?")

    if not exs:
        hist_rows = "<p class='ate-muted'>No exchanges in the current session yet.</p>"
    else:
        hist_rows = ""

        for idx, ex in enumerate(exs, 1):
            hist_rows += f"""
            <div class="ate-history-row">
                <div class="ate-history-meta">[{idx}] {ex.get('timestamp', '')}</div>
                <div><span class="ate-gold">Q:</span> {ex.get('question', '')[:160]}</div>
                <div class="ate-history-answer">
                    <span class="ate-gold">A:</span> {ex.get('answer_snippet', '')[:350]}…
                </div>
            </div>
            """

    with _qa_output:
        _ate_clear(wait=True)
        _ate_disp(_ate_HTML(f"""
        <div class="ate-output-panel">
            <div class="ate-kicker">◆ Session History ◆</div>
            <div class="ate-output-title">Session {sid} — {len(exs)} exchange(s)</div>
            {hist_rows}
        </div>
        """))


def _on_end(_b=None) -> None:
    for btn in (_qa_submit_btn, _qa_end_btn, _qa_history_btn, _qa_clear_btn):
        btn.disabled = True

    _qa_set_status("Research Engine closed.", "#e07070")

    with _qa_output:
        _ate_clear(wait=True)
        print("🛑 Closing Research Engine. Good luck with your assignment!")


def _on_submit(_b=None) -> None:
    question = _qa_text.value.strip()
    uploads = _get_upload_files()

    attachment_text = ""
    attachment_label = ""

    if uploads:
        _qa_upload.description = f"📎 Attach ({len(uploads)})"
        parts = []

        for fn, fc in uploads:
            try:
                extractor = ns.get('_extract_attachment_text')
                if callable(extractor):
                    parts.append(f"[Attachment: {fn}]\n{extractor(fn, fc)}")
                else:
                    parts.append(f"[Attachment: {fn}] (no extractor available)")
            except Exception as ae:
                parts.append(f"[Attachment: {fn}] extraction failed: {ae}")

        attachment_text = "\n\n".join(parts)
        attachment_label = ", ".join(fn for fn, _ in uploads)

    if not question and not attachment_text:
        _qa_set_status("⚠️ Please enter a question or attach a file.", "#e0a000")
        return

    full_question = question

    if attachment_text:
        full_question = (question + "\n\n" + attachment_text).strip() if question else attachment_text

    mode, _ = ns.get('_detect_prompt_mode', lambda q: ('unknown', None))(full_question)
    depth = f"{ns.get('RUNTIME_MODE','').upper()} · " if ns.get('RUNTIME_MODE') else ''

    _qa_set_status(
        f"🔍 Mode: {mode} | {depth}retrieval running…",
        "#4aa3ff",
    )

    _qa_submit_btn.disabled = True

    with _qa_output:
        _ate_clear(wait=True)

        if attachment_label:
            print(f"📎 Attachments: {attachment_label}")

        print(f"🔍 Mode: {mode} | {depth}retrieval running…")

    try:
        start = time.time()
        run_q = ns.get('run_academic_query', lambda q, max_attempts=1: {'answer':'', 'sources':[], 'retrieval_mode':'local'})
        result = run_q(full_question, max_attempts=3)
        append_ex = ns.get('_append_exchange')
        if callable(append_ex):
            append_ex(full_question, result)
        dur = time.time() - start

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        ret_mode = result.get("retrieval_mode", "unknown")

        with _qa_output:
            _ate_clear(wait=True)

            if ns.get('VISUAL_PANEL_ON') and 'render_answer_panel' in ns:
                try:
                    ns.get('render_answer_panel')(full_question, result)
                except Exception as rpe:
                    print(f"⚠️ Visual panel render failed: {rpe}")

                print(f"⏱️ {dur:.1f}s | {ret_mode}")

            else:
                print("\n" + "=" * 70)
                print("📝 ACADEMIC ANSWER")
                print("=" * 70)
                print(answer)
                print("=" * 70)
                print(f"⏱️ Completed in {dur:.1f} seconds.")
                print(f"🧭 Retrieval Mode: {ret_mode}")

                print("\n📍 SOURCES:")

                if not sources:
                    print("- No traceable source nodes returned for this answer.")
                else:
                    for ref in sources[: ns.get('SOURCE_PRINT_LIMIT', 10)]:
                        snip = ref.get("snippet") or "No snippet available"
                        print(
                            f"- [{ref.get('retriever')}] {ref.get('file_name')} | "
                            f"wing={ref.get('wing')} | room={ref.get('room')} | "
                            f"hall={ref.get('hall')} | drawer={ref.get('drawer_type')} | "
                            f'"{snip}..."'
                        )

        _qa_set_status(f"✅ Done in {dur:.1f}s | {ret_mode}", "#50c878")
        _qa_refresh_side()

    except Exception as submit_err:
        with _qa_output:
            print(f"⚠️ SYSTEM ERROR: {submit_err}")

        _qa_set_status(f"⚠️ Error: {submit_err}", "#e07070")

    finally:
        _qa_submit_btn.disabled = False
        _qa_clear_upload()


# ── Wire callbacks ───────────────────────────────────────────────
_qa_clear_btn.on_click(_on_clear)
_qa_history_btn.on_click(_show_history)
_qa_end_btn.on_click(_on_end)
_qa_submit_btn.on_click(_on_submit)


# ── CSS matching attached interface ───────────────────────────────
_ate_disp(_ate_HTML("""
<style>
.ate-shell {
    font-family: 'Segoe UI', Arial, sans-serif;
    background:
        radial-gradient(circle at bottom right, rgba(207,181,59,0.14), transparent 20%),
        linear-gradient(145deg, #0b0b0b 0%, #050505 70%);
    border-top: 3px solid #CFB53B;
    border-bottom: 3px solid #CFB53B;
    border-left: 3px solid #1A6FBF;
    border-right: 3px solid #1A6FBF;
    border-radius: 14px;
    padding: 18px;
    box-shadow:
        0 0 20px rgba(26,111,191,0.45),
        0 0 9px rgba(207,181,59,0.25);
    max-width: 1040px;
}

.ate-header-kicker {
    color: #CFB53B;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    text-align: right;
}

.ate-title {
    color: #f0f0e8;
    font-size: 24px;
    font-weight: 800;
    margin-bottom: 16px;
    text-align: right;
}

.ate-main-grid {
    display: grid;
    grid-template-columns: minmax(520px, 2fr) minmax(280px, 0.9fr);
    gap: 18px;
}

.ate-left-panel {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.ate-button-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.ate-info-bar {
    color: #e6e1c6;
    font-size: 14px;
    line-height: 1.8;
    border-top: 1px solid rgba(255,255,255,0.08);
    padding-top: 10px;
}

.ate-chip {
    display: inline-block;
    color: #f4df7a;
    border: 1px solid #CFB53B;
    border-radius: 999px;
    padding: 0 7px;
    margin: 2px;
    background: rgba(207,181,59,0.12);
    font-weight: 700;
}

.ate-right-stack {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.ate-card {
    background: linear-gradient(145deg, #111 0%, #090909 100%);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 10px;
    padding: 16px 18px;
    box-shadow: inset 0 0 0 1px rgba(207,181,59,0.08);
}

.ate-card-title {
    color: #f1edcc;
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(207,181,59,0.4);
    text-shadow: 0 0 5px rgba(207,181,59,0.25);
}

.ate-source-row {
    color: #f0f0e8;
    display: flex;
    gap: 10px;
    align-items: flex-start;
    font-size: 16px;
    line-height: 1.45;
    margin-bottom: 14px;
}

.ate-source-icon {
    font-size: 22px;
    width: 26px;
}

.ate-source-sub {
    color: #e2dba5;
}

.ate-source-ready {
    color: #8ee8ff;
}

.ate-status-line {
    color: #f0f0e8;
    font-family: Consolas, monospace;
    font-size: 16px;
    line-height: 1.9;
}

.ate-status-sub {
    color: #8b8b8b;
    font-family: Consolas, monospace;
    font-size: 13px;
    margin-bottom: 8px;
}

.ate-gold {
    color: #CFB53B;
    font-weight: 700;
}

.ate-muted {
    color: #8b8b8b;
    font-size: 13px;
    font-family: Consolas, monospace;
}

.ate-output-panel {
    margin-top: 14px;
    background: #0a0a0a;
    border: 1px solid #1A6FBF;
    border-radius: 10px;
    padding: 18px;
    color: #d4e8f8;
}

.ate-kicker {
    color: #CFB53B;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.ate-output-title {
    color: #d4e8f8;
    font-size: 18px;
    font-weight: 700;
    margin: 6px 0 14px;
}

.ate-history-row {
    border-left: 3px solid #CFB53B;
    padding: 10px 14px;
    background: #101010;
    border-radius: 6px;
    margin-bottom: 12px;
    color: #a0b8c8;
}

.ate-history-meta {
    font-size: 11px;
    color: #6a8fa8;
    margin-bottom: 4px;
}

.ate-history-answer {
    font-size: 13px;
    color: #a0b8c8;
    background: #080808;
    padding: 8px 12px;
    border-radius: 4px;
    border-left: 2px solid #1A6FBF;
    white-space: pre-wrap;
}

/* Textarea styling */
.ate-research-input textarea {
    background: linear-gradient(160deg, #272727 0%, #111 55%, #090909 100%) !important;
    color: #f2f2f2 !important;
    border: 1px solid #1A6FBF !important;
    border-radius: 10px !important;
    box-shadow:
        inset 0 2px 8px rgba(0,0,0,0.75),
        0 0 10px rgba(26,111,191,0.25) !important;
    font-family: Consolas, "Courier New", monospace !important;
    font-size: 20px !important;
    line-height: 1.45 !important;
    padding: 14px !important;
    caret-color: #CFB53B !important;
}

.ate-research-input textarea::placeholder {
    color: #eeeeee !important;
    opacity: 0.95 !important;
}

.widget-button {
    border-radius: 999px !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    box-shadow: 0 0 8px rgba(255,255,255,0.08) !important;
}

.widget-upload .jupyter-button,
.widget-upload button {
    border-radius: 999px !important;
    background: #2b2b2b !important;
    color: #f4f4f4 !important;
    border: 1px solid #555 !important;
    height: 42px !important;
}

.widget-output {
    background: #0a0a0a !important;
}
</style>
"""))


# ── Build rendered layout ─────────────────────────────────────────
_qa_refresh_side()

_control_row = _widgets.HBox(
    [_qa_upload, _qa_history_btn, _qa_clear_btn, _qa_end_btn],
    layout=_widgets.Layout(gap="8px", flex_flow="row wrap", align_items="center"),
)

_modes_html = _widgets.HTML("""
<div class="ate-info-bar">
    <strong>Modes</strong> — auto-detected from phrasing:
    <span class="ate-chip">essay</span>
    <span class="ate-chip">chat</span>
    <span class="ate-chip">summarise</span>
    <span class="ate-chip">paraphrase</span>
    <span class="ate-chip">formulate</span>
    <span class="ate-chip">retrieval</span>
    <br>
    <strong>Attachments</strong> — PDF · DOCX · XLSX · JPG / PNG / BMP / GIF (OCR) · SVG
</div>
""")

_left_col = _widgets.VBox(
    [
        _control_row,
        _qa_text,
        _modes_html,
        _widgets.HBox(
            [_qa_submit_btn, _qa_status],
            layout=_widgets.Layout(gap="12px", align_items="center"),
        ),
    ],
    layout=_widgets.Layout(width="100%", gap="10px"),
)

_header = _widgets.HTML(f"""
<div>
    <div class="ate-header-kicker">◆ Extended Interface / Live Analytics ◆ v1.1</div>
    <div class="ate-title">🏫 Research Engine Online</div>
</div>
""")

_grid = _widgets.HBox(
    [
        _widgets.VBox([_left_col], layout=_widgets.Layout(width="66%")),
        _widgets.VBox([_header, _qa_side], layout=_widgets.Layout(width="34%")),
    ],
    layout=_widgets.Layout(width="100%", gap="18px", align_items="flex-start"),
)

_outer = _widgets.VBox(
    [_grid, _qa_output],
    layout=_widgets.Layout(width="100%", max_width="1040px"),
)

_outer.add_class("ate-shell")

_ate_disp(_outer)
'''

    ns['ns'] = ns
    exec(code, ns)