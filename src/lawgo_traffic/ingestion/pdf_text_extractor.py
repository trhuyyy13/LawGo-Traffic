import re
from collections import Counter

_PAGE_NUMBER_PATTERN = re.compile(r"^\d{1,4}$")


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
