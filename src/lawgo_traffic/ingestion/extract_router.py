import subprocess
from pathlib import Path

from lawgo_traffic.ingestion.pdf_text_extractor import run_pdftotext

PDF_OCR_AVG_CHARS_PER_PAGE_THRESHOLD = 20


def _pdf_page_count(input_path: str) -> int:
    try:
        result = subprocess.run(
            ["pdfinfo", input_path], capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdfinfo not found — install poppler-utils (`brew install poppler` "
            "on macOS, `apt-get install poppler-utils` in Docker)"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"pdfinfo failed on {input_path}: {result.stderr.strip()}")
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"pdfinfo output for {input_path} has no 'Pages:' line")


def detect_format(filepath: str) -> str:
    """Return 'docx' | 'doc' | 'pdf_text' | 'pdf_ocr' for a raw input file."""
    suffix = Path(filepath).suffix.lower()
    if suffix == ".docx":
        return "docx"
    if suffix == ".doc":
        return "doc"
    if suffix == ".pdf":
        raw_text = run_pdftotext(filepath)
        pages = _pdf_page_count(filepath)
        avg_chars = len(raw_text.strip()) / pages if pages else 0
        return "pdf_ocr" if avg_chars < PDF_OCR_AVG_CHARS_PER_PAGE_THRESHOLD else "pdf_text"
    raise ValueError(f"Unsupported file extension '{suffix}' for {filepath}")
