import re
import subprocess
from collections import Counter
from pathlib import Path

from lawgo_traffic.ingestion.doc_id_map import get_doc_info
from lawgo_traffic.utils.text_normalizer import normalize_paragraph

_PAGE_NUMBER_PATTERN = re.compile(r"^\d{1,4}$")


def run_pdftotext(input_path: str) -> str:
    """Run poppler's pdftotext on input_path, return the full extracted text."""
    try:
        result = subprocess.run(
            ["pdftotext", input_path, "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdftotext not found — install poppler-utils (`brew install poppler` "
            "on macOS, `apt-get install poppler-utils` in Docker)"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed on {input_path}: {result.stderr.strip()}")
    return result.stdout


def _clean_pdf_lines(raw_text: str) -> list[str]:
    """Split pdftotext output into lines, dropping page numbers and repeated
    running headers/footers.

    pdftotext inserts a form-feed character ("\\f") between pages. We use
    that to find lines that repeat identically as the first non-empty line
    of 2+ pages (a running header) and drop them everywhere they occur.
    """
    pages = [page.split("\n") for page in raw_text.split("\f")]

    first_nonblank_per_page: list[str | None] = []
    for lines in pages:
        first = next((line.strip() for line in lines if line.strip()), None)
        first_nonblank_per_page.append(first)

    counts = Counter(line for line in first_nonblank_per_page if line is not None)
    repeated_headers = {line for line, n in counts.items() if n >= 2}

    cleaned: list[str] = []
    for lines in pages:
        header_skipped = False
        for line in lines:
            stripped = line.strip()
            if not header_skipped and stripped in repeated_headers:
                header_skipped = True
                continue
            if _PAGE_NUMBER_PATTERN.match(stripped):
                continue
            cleaned.append(line)
    return cleaned


def extract_pdf_to_text(input_path: str) -> dict:
    """Extract a single text-layer PDF and return the same contract as
    docx_extractor.extract_docx_to_text().
    """
    info = get_doc_info(input_path)
    raw_text = run_pdftotext(input_path)
    lines = _clean_pdf_lines(raw_text)
    paragraphs = [normalize_paragraph(line) for line in lines]
    return {
        "source_file": Path(input_path).name,
        "doc_id": info["doc_id"],
        "document_title": info["document_title"],
        "paragraphs": paragraphs,
        "extraction_method": "pdf_text",
    }
