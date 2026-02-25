# 🎓 Academic Truth Engine: Project README

**Purpose:** This notebook ingests a PDF (from Google Drive), semantically chunks it, and runs an evidence-first research loop using a retrieval-augmented generation (RAG) pipeline.

## Quick Setup (Windows PowerShell)

1. Open PowerShell and change directory to the repository root (the folder containing the notebook):

```powershell
cd C:\path\to\Academic-Truth-Engine
```

2. Install Jupyter and ipywidgets (using the specified PyPI mirror):

```powershell
python -m pip install notebook ipywidgets -i https://pypi.tuna.tsinghua.edu.cn/simple
```

3. Activate the virtual environment:

```powershell
.\venv\Scripts\activate
```

4. Inside the virtual environment, launch the notebook:

```powershell
jupyter notebook Academic_Truth_Engine_v2.ipynb
```

## Additional Python / System Dependencies

- The notebook requires several Python packages (the first notebook cell installs them), including OCR-related packages: `pytesseract`, `pdf2image`, `Pillow`, and `PyMuPDF`.
- For OCR fallback to work you must also install system tools:
  - Tesseract OCR executable: https://github.com/tesseract-ocr/tesseract
  - Poppler utilities (for `pdf2image`): https://poppler.freedesktop.org/

If those executables are missing, the notebook will fall back to plain PDF text extraction and print instructions.

## How the Notebook Handles PDFs

- The notebook attempts to download a PDF from Google Drive when you paste a share link.
- It first tries to extract selectable text using `PyMuPDF`.
- If the PDF is scanned/image-only or contains no extractable text, the notebook falls back to OCR using `pdf2image` + `pytesseract` and generates a `.ocr.txt` file which is then ingested.

## Notes & Troubleshooting

- If Google Drive links prompt for a permission or require interactive confirmation, ensure the file is shareable (anyone with link can view) or download the PDF manually into the `academic_data` folder and name it `source_material.pdf`.
- If OCR is slow or produces noisy text, consider preprocessing the PDF (deskew, increase DPI) or using a higher-quality Tesseract language model.

## Running

1. Open [Academic_Truth_Engine_v2.ipynb](Academic_Truth_Engine_v2.ipynb) in Jupyter.
2. Run the cells in order. When prompted, paste your Google Drive link.
3. After ingestion and parsing, ask research questions in the interactive loop.

## Console & Logs

- The notebook includes an interactive console widget (a scrollable output pane) displayed near the top of the notebook. Operational logs, warnings, and errors from ingestion, extraction, OCR, and retrieval stages are written to that console.
- What you'll see: startup confirmations, model/setup status, download and extraction messages, OCR success/failure, semantic node counts, and query-run errors or summaries. Logs include timestamps and severity.
- The console is implemented with `ipywidgets.Output`; you do not need a separate terminal to view runtime logs.

## Diagnostics (optional)

- An optional diagnostics cell can verify system tools required for OCR:
  - Checks for the Tesseract executable and prints its version.
  - Attempts a small `pdf2image` conversion to verify Poppler availability.
- If a check fails, the diagnostics cell prints installation suggestions and links.

## Troubleshooting Quick Commands

If Tesseract or Poppler are missing, common Windows install suggestions (Chocolatey):

```powershell
# Install Tesseract (requires Chocolatey)
choco install tesseract

# Install Poppler (requires Chocolatey)
choco install poppler
```

After installing, restart your terminal/Jupyter kernel and re-run the diagnostics cell.

## Virtualenv: install specific packages and register Jupyter kernel

If you need to force-install specific packages inside the project's virtual environment and register that venv as a dedicated Jupyter kernel, run the following from the activated `venv`:

```powershell
# 1. Force install the specific missing modules
python -m pip install --default-timeout=100 llama-index-llms-replicate replicate llama-index-embeddings-huggingface

# 2. Register this venv as a dedicated Jupyter Kernel
python -m pip install ipykernel
python -m ipykernel install --user --name=AcademicEngine --display-name "Python (Academic Engine)"
```

After installing and registering the kernel, restart Jupyter Notebook and select the kernel named "Python (Academic Engine)" from the Kernel menu to run the notebook inside this environment.

---
