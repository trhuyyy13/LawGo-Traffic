# Multi-format Ingestion (PDF text-layer + OCR) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `data/raw/` contain `.docx`, `.doc`, and `.pdf` (text-layer or scanned) files and have all of them flow through the existing `legal_parser.py` / `chunk_builder.py` unchanged, by adding new extractors that all produce the same `{source_file, doc_id, document_title, paragraphs}` contract.

**Architecture:** A new `extract_router.py` detects each raw file's format (`docx` / `doc` / `pdf_text` / `pdf_ocr`) and dispatches to the matching extractor. `.doc` is converted to `.docx` via headless LibreOffice and reuses the existing `docx_extractor`. PDFs with a real text layer go through a new `pdftotext`-based extractor. Scanned PDFs (no text layer) go through a new OCR extractor that calls an OpenAI vision model, gated behind `OCR_ENABLED`.

**Tech Stack:** Python 3.11, `subprocess` calls to `pdftotext`/`pdfinfo`/`pdfimages` (poppler-utils) and `soffice` (LibreOffice headless), `openai` SDK (already a dependency) for OCR, `tenacity` (already a dependency) for retry.

## Global Constraints

- `legal_parser.py` must end this plan with **zero diff** — every new extractor must conform to the existing `paragraphs: list[str]` contract (verified: the parser already merges non-structural continuation lines into the current block, so PDF line-wrapping is tolerated without parser changes).
- `docx_extractor.py` must also end with **zero diff** — reuse `extract_docx_paragraphs()` / `extract_docx_to_text()` as-is.
- `chunk_builder.py` gets exactly **one additive change** (Task 8's W08 warning) — everything else in it (chunk-building logic, W01/W02/W04-W07) stays untouched. This is a deliberate, narrow exception to the "don't touch the parser/chunk pipeline" idea behind spec 04; it does not change any existing chunk's shape or any existing warning's behavior.
- OCR must be gated by `settings.ocr_enabled` (mirrors the existing `voice_enabled` pattern in `config.py`) and must reuse `settings.llm_api_key` — no second API key.
- No OCR call in any unit test — OCR network calls are mocked; the only place a real OpenAI call happens is the final manual ingestion run (Task 12), which requires the user's real key in `.env`.
- New ngưỡng (threshold) for scanned-PDF detection: average extracted chars/page < 20 (measured on real files: scanned doc ≈ 1 char/page, every text-layer doc ≥ thousands of chars/page — large safety margin, do not tune further in this plan).

---

### Task 0: Fix broken build backend and confirm the test suite actually runs

The project's `pyproject.toml` has `build-backend = "setuptools.backends.legacy:build"`, which is not a real entry point — `pip install -e .` fails immediately with `BackendUnavailable: Cannot import 'setuptools.backends.legacy'`. This has apparently never been hit because every existing ingestion test is a `pytest.skip("Not implemented yet")` stub. This must be fixed first, or none of the tests in this plan can run.

**Files:**
- Modify: `pyproject.toml:3`

**Interfaces:**
- N/A (build config only)

- [ ] **Step 1: Fix the build backend**

In `pyproject.toml`, change:
```toml
build-backend = "setuptools.backends.legacy:build"
```
to:
```toml
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Install the package in editable mode**

Run: `pip install -e ".[dev]"`
Expected: completes with `Successfully installed lawgo-traffic-0.1.0` (or similar), no `BackendUnavailable` error.

- [ ] **Step 3: Confirm pytest can import the package**

Run: `pytest tests/ -v`
Expected: all current tests run and report `SKIPPED (Not implemented yet)` — zero `ERROR`/`ModuleNotFoundError`. This confirms the import path works; the skips are expected (those tests belong to spec 01, not this plan).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "fix: correct broken setuptools build-backend so pip install -e works"
```

---

### Task 1: Create test fixtures (PDF text-layer, PDF scanned, legacy .doc)

We need three real binary fixtures, generated from the existing `tests/fixtures/sample_law_text.txt`, to test the new extractors against real `pdftotext`/`pdfimages`/`soffice` output instead of guessing at it.

**Files:**
- Create: `tests/fixtures/sample_law_text.pdf` (binary, generated)
- Create: `tests/fixtures/sample_law_text.doc` (binary, generated)
- Create: `tests/fixtures/sample_pdf_scanned_2page.pdf` (binary, generated)
- Create: `tests/fixtures/_generate_scanned_pdf_fixture.py` (kept so the binary is reproducible)

**Interfaces:**
- N/A (test data only)

- [ ] **Step 1: Generate the text-layer PDF fixture**

Run:
```bash
soffice --headless --convert-to pdf --outdir tests/fixtures tests/fixtures/sample_law_text.txt
```
Expected: `tests/fixtures/sample_law_text.pdf` created. Verify it round-trips correctly:
```bash
pdftotext tests/fixtures/sample_law_text.pdf -
```
Expected output (line-wrapped, this wrapping is exactly what `_clean_pdf_lines`/parser continuation-merge must tolerate — see Task 3):
```
Chương II
XỬ PHẠT VI PHẠM HÀNH CHÍNH TRONG LĨNH VỰC GIAO THÔNG ĐƯỜNG BỘ
Điều 7. Xử phạt người điều khiển xe mô tô, xe gắn máy (kể cả xe máy điện), các
loại xe tương tự xe mô tô và các loại xe tương tự xe gắn máy vi phạm quy tắc
giao thông đường bộ
4. Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng đối với người điều khiển xe
thực hiện một trong các hành vi vi phạm sau đây:
a) Không chấp hành hiệu lệnh của đèn tín hiệu giao thông;
b) Điều khiển xe đi ngược chiều của đường một chiều, đi ngược chiều trên đường
có biển "Cấm đi ngược chiều";
```

- [ ] **Step 2: Generate the legacy `.doc` fixture (for Task 6's `convert_doc_to_docx`)**

Run:
```bash
soffice --headless --convert-to doc:"MS Word 97" --outdir tests/fixtures tests/fixtures/sample_law_text.txt
```
Expected: `tests/fixtures/sample_law_text.doc` created (a real binary `.doc`, not a renamed `.docx`).

- [ ] **Step 3: Write the scanned-PDF fixture generator**

Create `tests/fixtures/_generate_scanned_pdf_fixture.py`:
```python
"""Regenerate tests/fixtures/sample_pdf_scanned_2page.pdf.

Run manually if the fixture needs to change:
    python tests/fixtures/_generate_scanned_pdf_fixture.py
Produces a 2-page PDF with embedded images and NO text layer — used to test
the scanned-PDF detection heuristic and the OCR extractor's page-image
extraction, without needing a real scanned legal document in tests/.
"""
from pathlib import Path

from PIL import Image

OUT_PATH = Path(__file__).parent / "sample_pdf_scanned_2page.pdf"


def main() -> None:
    page1 = Image.new("RGB", (600, 800), color=(255, 255, 255))
    page2 = Image.new("RGB", (600, 800), color=(240, 240, 240))
    page1.save(OUT_PATH, "PDF", save_all=True, append_images=[page2])
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the generator**

Run: `python tests/fixtures/_generate_scanned_pdf_fixture.py`
Expected: `Wrote tests/fixtures/sample_pdf_scanned_2page.pdf`. Verify:
```bash
pdfinfo tests/fixtures/sample_pdf_scanned_2page.pdf | grep Pages
pdftotext tests/fixtures/sample_pdf_scanned_2page.pdf - | wc -c
```
Expected: `Pages: 2` and a byte count near 0 (no extractable text — this is what makes it a valid "scanned" fixture).

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/sample_law_text.pdf tests/fixtures/sample_law_text.doc \
        tests/fixtures/sample_pdf_scanned_2page.pdf \
        tests/fixtures/_generate_scanned_pdf_fixture.py
git commit -m "test: add PDF/doc/scanned fixtures for multi-format ingestion"
```

---

### Task 2: Extend `doc_id_map.py` with the 9 new documents

**Files:**
- Modify: `src/lawgo_traffic/ingestion/doc_id_map.py`
- Test: `tests/test_doc_id_map.py` (new)

**Interfaces:**
- Consumes: nothing new
- Produces: `get_doc_info(filepath: str) -> dict[str, str]` now resolves 9 additional filenames (used by Tasks 4, 6, 7, 9)

- [ ] **Step 1: Write the failing test**

Create `tests/test_doc_id_map.py`:
```python
import pytest

from lawgo_traffic.ingestion.doc_id_map import get_doc_info


@pytest.mark.parametrize(
    "filename,expected_doc_id",
    [
        ("Luat-15-2012-QH13-XLVPHC.doc", "luat_xlvphc_2012"),
        ("Luat-67-2020-QH14-XLVPHC-suadoi.pdf", "luat_xlvphc_2020"),
        ("Luat-88-2025-QH15-XLVPHC-suadoi.pdf", "luat_xlvphc_2025"),
        ("Thong-tu-35-2024-TT-BGTVT-daotao-GPLX.pdf", "tt35_2024_bgtvt"),
        ("Thong-tu-12-2025-TT-BCA-sathach-capGPLX.pdf", "tt12_2025_bca"),
        ("Thong-tu-47-2024-TT-BGTVT-kiemdinh-xecogioi.pdf", "tt47_2024_bgtvt"),
        ("Nghi-dinh-67-2023-ND-CP-baohiem-bat-buoc-xecogioi.pdf", "nd67_2023"),
        ("Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf", "tt72_2024_bca"),
        ("Thong-tu-51-2024-TT-BGTVT-QCVN41-2024-baohieuduongbo.pdf", "tt51_2024_bgtvt"),
    ],
)
def test_new_documents_resolve(filename, expected_doc_id):
    info = get_doc_info(filename)
    assert info["doc_id"] == expected_doc_id
    assert info["document_title"]  # non-empty
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_doc_id_map.py -v`
Expected: all 9 parametrized cases FAIL with `KeyError: "Unknown source file ..."`.

- [ ] **Step 3: Add the entries**

In `src/lawgo_traffic/ingestion/doc_id_map.py`, add to `DOC_ID_MAP` (after the existing 5 entries, before the closing `}`):
```python
    "Luat-15-2012-QH13-XLVPHC.doc": {
        "doc_id": "luat_xlvphc_2012",
        "document_title": "Luật Xử lý vi phạm hành chính 15/2012/QH13",
    },
    "Luat-67-2020-QH14-XLVPHC-suadoi.pdf": {
        "doc_id": "luat_xlvphc_2020",
        "document_title": "Luật sửa đổi, bổ sung một số điều của Luật Xử lý vi phạm hành chính 67/2020/QH14",
    },
    "Luat-88-2025-QH15-XLVPHC-suadoi.pdf": {
        "doc_id": "luat_xlvphc_2025",
        "document_title": "Luật sửa đổi, bổ sung một số điều của Luật Xử lý vi phạm hành chính 88/2025/QH15",
    },
    "Thong-tu-35-2024-TT-BGTVT-daotao-GPLX.pdf": {
        "doc_id": "tt35_2024_bgtvt",
        "document_title": "Thông tư 35/2024/TT-BGTVT",
    },
    "Thong-tu-12-2025-TT-BCA-sathach-capGPLX.pdf": {
        "doc_id": "tt12_2025_bca",
        "document_title": "Thông tư 12/2025/TT-BCA",
    },
    "Thong-tu-47-2024-TT-BGTVT-kiemdinh-xecogioi.pdf": {
        "doc_id": "tt47_2024_bgtvt",
        "document_title": "Thông tư 47/2024/TT-BGTVT",
    },
    "Nghi-dinh-67-2023-ND-CP-baohiem-bat-buoc-xecogioi.pdf": {
        "doc_id": "nd67_2023",
        "document_title": "Nghị định 67/2023/NĐ-CP",
    },
    "Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf": {
        "doc_id": "tt72_2024_bca",
        "document_title": "Thông tư 72/2024/TT-BCA",
    },
    "Thong-tu-51-2024-TT-BGTVT-QCVN41-2024-baohieuduongbo.pdf": {
        "doc_id": "tt51_2024_bgtvt",
        "document_title": "Thông tư 51/2024/TT-BGTVT",
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_doc_id_map.py -v`
Expected: all 9 cases PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/doc_id_map.py tests/test_doc_id_map.py
git commit -m "feat: register 9 new legal documents in DOC_ID_MAP"
```

---

### Task 3: `pdf_text_extractor.py` — line cleanup (`_clean_pdf_lines`)

This is the part of spec 04 §5 step 4 that strips lone page-number lines and repeated running headers/footers. Built as a pure function first (no subprocess) so it's trivially unit-testable.

**Files:**
- Create: `src/lawgo_traffic/ingestion/pdf_text_extractor.py`
- Test: `tests/test_pdf_text_extractor.py` (new)

**Interfaces:**
- Produces: `_clean_pdf_lines(raw_text: str) -> list[str]` (consumed by `extract_pdf_to_text` in Task 4)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pdf_text_extractor.py`:
```python
from lawgo_traffic.ingestion.pdf_text_extractor import _clean_pdf_lines


def test_strips_lone_page_number_lines():
    raw = "Điều 1. Nội dung\n1\nKhoản 1 tiếp tục"
    lines = _clean_pdf_lines(raw)
    assert "1" not in lines
    assert "Điều 1. Nội dung" in lines
    assert "Khoản 1 tiếp tục" in lines


def test_strips_repeated_header_across_pages():
    raw = (
        "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐiều 1. Nội dung trang 1\n"
        "\f"
        "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐiều 2. Nội dung trang 2"
    )
    lines = _clean_pdf_lines(raw)
    assert lines.count("CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM") == 0
    assert "Điều 1. Nội dung trang 1" in lines
    assert "Điều 2. Nội dung trang 2" in lines


def test_keeps_line_that_only_appears_once():
    raw = "Điều 1. Tiêu đề riêng\nNội dung\n\fĐiều 2. Tiêu đề khác\nNội dung khác"
    lines = _clean_pdf_lines(raw)
    assert "Điều 1. Tiêu đề riêng" in lines
    assert "Điều 2. Tiêu đề khác" in lines
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pdf_text_extractor.py -v`
Expected: FAIL with `ImportError` / `ModuleNotFoundError` (module doesn't exist yet).

- [ ] **Step 3: Implement `_clean_pdf_lines`**

Create `src/lawgo_traffic/ingestion/pdf_text_extractor.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pdf_text_extractor.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/pdf_text_extractor.py tests/test_pdf_text_extractor.py
git commit -m "feat: add PDF line cleanup (page numbers, repeated headers)"
```

---

### Task 4: `pdf_text_extractor.py` — `run_pdftotext` + `extract_pdf_to_text`

**Files:**
- Modify: `src/lawgo_traffic/ingestion/pdf_text_extractor.py`
- Test: `tests/test_pdf_text_extractor.py`

**Interfaces:**
- Consumes: `get_doc_info` from `lawgo_traffic.ingestion.doc_id_map` (Task 2), `normalize_paragraph` from `lawgo_traffic.utils.text_normalizer` (existing)
- Produces: `run_pdftotext(input_path: str) -> str` (reused by `extract_router.detect_format` in Task 5), `extract_pdf_to_text(input_path: str) -> dict` (consumed by `extract_router.extract_all` in Task 9)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pdf_text_extractor.py`:
```python
from pathlib import Path

import pytest

from lawgo_traffic.ingestion.pdf_text_extractor import extract_pdf_to_text, run_pdftotext

FIXTURE = "tests/fixtures/sample_law_text.pdf"


def test_run_pdftotext_returns_nonempty_text():
    text = run_pdftotext(FIXTURE)
    assert "Điều 7" in text


def test_run_pdftotext_missing_binary_raises(monkeypatch):
    # Point PATH somewhere with no executables so subprocess.run can't
    # resolve "pdftotext" and raises FileNotFoundError internally.
    monkeypatch.setenv("PATH", "/nonexistent")
    with pytest.raises(RuntimeError, match="pdftotext not found"):
        run_pdftotext(FIXTURE)


def test_extract_pdf_to_text_matches_contract(tmp_path):
    # Copy the fixture under a filename already registered in DOC_ID_MAP
    # (Task 2) so get_doc_info() resolves it without touching the map again.
    fixture_copy = tmp_path / "Nghi-dinh-67-2023-ND-CP-baohiem-bat-buoc-xecogioi.pdf"
    fixture_copy.write_bytes(Path(FIXTURE).read_bytes())

    data = extract_pdf_to_text(str(fixture_copy))

    assert data["doc_id"] == "nd67_2023"
    assert data["document_title"] == "Nghị định 67/2023/NĐ-CP"
    assert data["source_file"] == fixture_copy.name
    assert data["extraction_method"] == "pdf_text"
    assert any("Điều 7" in p for p in data["paragraphs"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pdf_text_extractor.py -v`
Expected: the 3 new tests FAIL with `ImportError` (`run_pdftotext`/`extract_pdf_to_text` don't exist yet).

- [ ] **Step 3: Implement**

Add to `src/lawgo_traffic/ingestion/pdf_text_extractor.py` (after the imports, before `_clean_pdf_lines`):
```python
import subprocess
from pathlib import Path

from lawgo_traffic.ingestion.doc_id_map import get_doc_info
from lawgo_traffic.utils.text_normalizer import normalize_paragraph


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
```

Add at the end of the file:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pdf_text_extractor.py -v`
Expected: all 6 tests PASS (3 from Task 3 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/pdf_text_extractor.py tests/test_pdf_text_extractor.py
git commit -m "feat: extract text-layer PDFs via pdftotext into the docx_extractor contract"
```

---

### Task 5: `extract_router.py` — `detect_format`

**Files:**
- Create: `src/lawgo_traffic/ingestion/extract_router.py`
- Test: `tests/test_extract_router.py` (new)

**Interfaces:**
- Consumes: `run_pdftotext` from `pdf_text_extractor` (Task 4)
- Produces: `detect_format(filepath: str) -> str` (returns `"docx" | "doc" | "pdf_text" | "pdf_ocr"`; consumed by `extract_all` in Task 9)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_extract_router.py`:
```python
import pytest

from lawgo_traffic.ingestion.extract_router import detect_format

TEXT_PDF = "tests/fixtures/sample_law_text.pdf"
SCANNED_PDF = "tests/fixtures/sample_pdf_scanned_2page.pdf"


def test_docx_extension():
    assert detect_format("anything.docx") == "docx"


def test_doc_extension():
    assert detect_format("anything.doc") == "doc"


def test_pdf_with_text_layer():
    assert detect_format(TEXT_PDF) == "pdf_text"


def test_pdf_scanned_no_text_layer():
    assert detect_format(SCANNED_PDF) == "pdf_ocr"


def test_unsupported_extension_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        detect_format("anything.txt")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extract_router.py -v`
Expected: FAIL with `ModuleNotFoundError` (module doesn't exist yet).

- [ ] **Step 3: Implement**

Create `src/lawgo_traffic/ingestion/extract_router.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extract_router.py -v`
Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/extract_router.py tests/test_extract_router.py
git commit -m "feat: detect raw file format (docx/doc/pdf_text/pdf_ocr)"
```

---

### Task 6: `extract_router.py` — `convert_doc_to_docx`

**Files:**
- Modify: `src/lawgo_traffic/ingestion/extract_router.py`
- Test: `tests/test_extract_router.py`

**Interfaces:**
- Produces: `convert_doc_to_docx(input_path: str, output_dir: str) -> str` (consumed by `extract_all` in Task 9)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_extract_router.py`:
```python
from lawgo_traffic.ingestion.docx_extractor import extract_docx_paragraphs
from lawgo_traffic.ingestion.extract_router import convert_doc_to_docx

DOC_FIXTURE = "tests/fixtures/sample_law_text.doc"


def test_convert_doc_to_docx_produces_readable_docx(tmp_path):
    out_path = convert_doc_to_docx(DOC_FIXTURE, str(tmp_path))
    assert out_path.endswith(".docx")

    paragraphs = extract_docx_paragraphs(out_path)
    assert any("Điều 7" in p for p in paragraphs)


def test_convert_doc_to_docx_missing_binary_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", "/nonexistent")
    with pytest.raises(RuntimeError, match="soffice not found"):
        convert_doc_to_docx(DOC_FIXTURE, str(tmp_path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extract_router.py -v`
Expected: 2 new FAIL with `ImportError` (`convert_doc_to_docx` doesn't exist yet).

- [ ] **Step 3: Implement**

Add to `src/lawgo_traffic/ingestion/extract_router.py`:
```python
def convert_doc_to_docx(input_path: str, output_dir: str) -> str:
    """Convert a legacy .doc file to .docx via headless LibreOffice.

    Returns the path to the converted .docx file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "docx", "--outdir", output_dir, input_path],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "soffice not found — install LibreOffice "
            "(`brew install --cask libreoffice` on macOS, "
            "`apt-get install libreoffice-writer` in Docker)"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"soffice conversion failed on {input_path}: {result.stderr.strip()}")

    converted = Path(output_dir) / (Path(input_path).stem + ".docx")
    if not converted.exists():
        raise RuntimeError(f"soffice did not produce expected output: {converted}")
    return str(converted)
```

Add `from pathlib import Path` is already imported in this file (Task 5) — no new import needed beyond what Task 5 added.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_extract_router.py -v`
Expected: all 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/extract_router.py tests/test_extract_router.py
git commit -m "feat: convert legacy .doc files to .docx via headless LibreOffice"
```

---

### Task 7: `pdf_ocr_extractor.py` — scanned-PDF OCR via OpenAI vision

**Files:**
- Create: `src/lawgo_traffic/ingestion/pdf_ocr_extractor.py`
- Test: `tests/test_pdf_ocr_extractor.py` (new)

**Interfaces:**
- Consumes: `get_doc_info` (Task 2), `normalize_paragraph` (existing), `settings` from `lawgo_traffic.config` (existing, already has `ocr_model`/`llm_api_key` fields)
- Produces: `extract_scanned_pdf_to_text(input_path: str) -> dict` (consumed by `extract_all` in Task 9)

**Important:** no test in this task makes a real network call. `_ocr_page` is monkeypatched in every test that exercises `extract_scanned_pdf_to_text`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pdf_ocr_extractor.py`:
```python
from pathlib import Path

from lawgo_traffic.ingestion import pdf_ocr_extractor
from lawgo_traffic.ingestion.pdf_ocr_extractor import (
    _extract_page_images,
    extract_scanned_pdf_to_text,
)

SCANNED_FIXTURE = "tests/fixtures/sample_pdf_scanned_2page.pdf"


def test_extract_page_images_returns_one_image_per_page(tmp_path):
    images = _extract_page_images(SCANNED_FIXTURE, str(tmp_path))
    assert len(images) == 2
    for img in images:
        assert Path(img).exists()


def test_extract_scanned_pdf_to_text_uses_mocked_ocr(monkeypatch, tmp_path):
    fixture_copy = tmp_path / "Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf"
    fixture_copy.write_bytes(Path(SCANNED_FIXTURE).read_bytes())

    page_texts = iter(["Điều 1. Trang một", "Điều 2. Trang hai"])
    monkeypatch.setattr(
        pdf_ocr_extractor, "_ocr_page", lambda client, image_path: next(page_texts)
    )

    data = extract_scanned_pdf_to_text(str(fixture_copy))

    assert data["doc_id"] == "tt72_2024_bca"
    assert data["extraction_method"] == "pdf_ocr"
    assert any("Điều 1. Trang một" in p for p in data["paragraphs"])
    assert any("Điều 2. Trang hai" in p for p in data["paragraphs"])


def test_extract_scanned_pdf_to_text_preserves_page_order(monkeypatch, tmp_path):
    fixture_copy = tmp_path / "Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf"
    fixture_copy.write_bytes(Path(SCANNED_FIXTURE).read_bytes())

    seen_images: list[str] = []

    def fake_ocr_page(client, image_path):
        seen_images.append(image_path)
        return f"text for {Path(image_path).name}"

    monkeypatch.setattr(pdf_ocr_extractor, "_ocr_page", fake_ocr_page)
    extract_scanned_pdf_to_text(str(fixture_copy))

    assert seen_images == sorted(seen_images)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pdf_ocr_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError` (module doesn't exist yet).

- [ ] **Step 3: Implement**

Create `src/lawgo_traffic/ingestion/pdf_ocr_extractor.py`:
```python
import base64
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from lawgo_traffic.config import settings
from lawgo_traffic.ingestion.doc_id_map import get_doc_info
from lawgo_traffic.utils.text_normalizer import normalize_paragraph

OCR_PROMPT = """\
Đây là ảnh scan một trang văn bản pháp luật Việt Nam. Hãy phiên âm (transcribe)
CHÍNH XÁC TỪNG CHỮ những gì nhìn thấy trong ảnh, theo các quy tắc sau:

1. KHÔNG diễn giải, KHÔNG tóm tắt, KHÔNG sửa lỗi chính tả, KHÔNG thêm nội dung
   không có trong ảnh.
2. Giữ nguyên chính xác số hiệu Điều, Khoản, Điểm (ví dụ "Điều 5.", "2.", "a)")
   — đây là phần quan trọng nhất, sai một số là sai trích dẫn pháp lý.
3. Giữ nguyên ngắt đoạn: mỗi Điều/Khoản/Điểm xuống dòng riêng như trong ảnh.
4. Nếu có chữ không đọc được rõ, đánh dấu bằng [KHÔNG RÕ: <phần đoán tốt nhất>]
   thay vì bỏ qua hoặc đoán bừa không đánh dấu.
5. Bỏ qua header/footer/số trang/dấu mộc/chữ ký scan — chỉ lấy nội dung văn bản.
6. Output thuần text, không markdown, không thêm chú thích ngoài nội dung gốc.
"""


def _extract_page_images(input_path: str, tmp_dir: str) -> list[str]:
    """Extract each page's embedded original image via pdfimages.

    Returns image paths sorted in page order (pdfimages names them
    "<prefix>-000.<ext>", "<prefix>-001.<ext>", ... so a plain sort is
    page-order-correct).
    """
    prefix = str(Path(tmp_dir) / "page")
    try:
        result = subprocess.run(
            ["pdfimages", "-all", input_path, prefix],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdfimages not found — install poppler-utils (`brew install poppler` "
            "on macOS, `apt-get install poppler-utils` in Docker)"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"pdfimages failed on {input_path}: {result.stderr.strip()}")

    images = sorted(str(p) for p in Path(tmp_dir).glob("page-*"))
    if not images:
        raise RuntimeError(f"pdfimages produced no images for {input_path}")
    return images


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def _ocr_page(client: OpenAI, image_path: str) -> str:
    """Call the configured OpenAI vision model on a single page image."""
    image_bytes = Path(image_path).read_bytes()
    b64 = base64.b64encode(image_bytes).decode("ascii")
    ext = Path(image_path).suffix.lstrip(".") or "jpeg"

    response = client.chat.completions.create(
        model=settings.ocr_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/{ext};base64,{b64}"},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content or ""


def extract_scanned_pdf_to_text(input_path: str) -> dict:
    """Extract a scanned (no text layer) PDF via OCR.

    Returns the same contract as docx_extractor.extract_docx_to_text(), plus
    extraction_method="pdf_ocr". Each page's raw OCR response is also saved
    to data/extracted/_ocr_debug/<doc_id>_page_<n>.txt for manual review —
    OCR-derived text needs more scrutiny than docx/pdf_text extraction.
    """
    info = get_doc_info(input_path)
    doc_id = info["doc_id"]

    client = OpenAI(api_key=settings.llm_api_key)
    debug_dir = Path("data/extracted/_ocr_debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        image_paths = _extract_page_images(input_path, tmp_dir)
        page_texts: list[str] = []
        for idx, image_path in enumerate(image_paths, start=1):
            text = _ocr_page(client, image_path)
            page_texts.append(text)
            (debug_dir / f"{doc_id}_page_{idx}.txt").write_text(text, encoding="utf-8")

    raw_text = "\n".join(page_texts)
    paragraphs = [normalize_paragraph(line) for line in raw_text.split("\n")]

    return {
        "source_file": Path(input_path).name,
        "doc_id": doc_id,
        "document_title": info["document_title"],
        "paragraphs": paragraphs,
        "extraction_method": "pdf_ocr",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pdf_ocr_extractor.py -v`
Expected: all 3 PASS. No network call is made (verify by running with no internet / unset `OPENAI` env vars — should still pass since `_ocr_page` is monkeypatched in every test).

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/pdf_ocr_extractor.py tests/test_pdf_ocr_extractor.py
git commit -m "feat: OCR scanned PDFs via OpenAI vision with verbatim-transcription prompt"
```

---

### Task 8: `chunk_builder.py` — W08 warning for low-confidence OCR text

**Files:**
- Modify: `src/lawgo_traffic/ingestion/chunk_builder.py:239-243` (add block right after the existing W04 check)
- Modify: `scripts/build_chunks.py:69` (add `"W08"` to `critical_codes`)
- Test: `tests/test_chunk_builder.py` (add one new test; leave existing `pytest.skip` stubs alone — they belong to spec 01, not this plan)

**Interfaces:**
- Consumes: nothing new — scans `children[i]["text_raw"]` for the literal marker `"[KHÔNG RÕ:"` that `pdf_ocr_extractor`'s prompt instructs the model to emit (Task 7)
- Note: `build_validation_report`'s existing warning codes are W01 (orphan clause), W02 (orphan point), W04 (short text), W05 (duplicate chunk_id), W06 (missing clause_header), W07 (ARTICLE_CHILD conflict) — confirmed by reading the file. **W05 is already taken**, so this plan uses **W08**, not the W05 mentioned in spec 04 §8 (that section of the spec was written before checking the existing code; W08 is the correct, non-colliding choice).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_chunk_builder.py` (new test function, keep existing skipped ones untouched):
```python
from lawgo_traffic.ingestion.chunk_builder import build_validation_report
from lawgo_traffic.ingestion.legal_parser import ArticleBlock, ClauseBlock, PointBlock


def test_low_confidence_ocr_marker_produces_w08_warning():
    article = ArticleBlock(
        doc_id="tt72_2024_bca",
        document_title="Thông tư 72/2024/TT-BCA",
        source_file="Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf",
        chapter=None,
        chapter_title=None,
        section=None,
        section_title=None,
        article_number="1",
        article_title="Phạm vi điều chỉnh",
    )
    article.clauses = [
        ClauseBlock(number="1", clause_header="Khoản 1"),
    ]
    article.clauses[0].points = [
        PointBlock(letter="a", text_raw="Nội dung rõ ràng"),
        PointBlock(letter="b", text_raw="Nội dung [KHÔNG RÕ: mờ chữ] không chắc"),
    ]

    children = [
        {"chunk_id": "tt72_2024_bca_dieu_1_khoan_1_diem_a", "chunk_type": "POINT",
         "text_raw": "Nội dung rõ ràng", "clause_header": "Khoản 1"},
        {"chunk_id": "tt72_2024_bca_dieu_1_khoan_1_diem_b", "chunk_type": "POINT",
         "text_raw": "Nội dung [KHÔNG RÕ: mờ chữ] không chắc", "clause_header": "Khoản 1"},
    ]

    report = build_validation_report(
        "Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf",
        "tt72_2024_bca",
        [article],
        parents=[],
        children=children,
    )

    w08_warnings = [w for w in report["warnings"] if w.startswith("W08")]
    assert len(w08_warnings) == 1
    assert "tt72_2024_bca_dieu_1_khoan_1_diem_b" in w08_warnings[0]
```

(Field names above are verified against `src/lawgo_traffic/ingestion/legal_parser.py:37-61` — `PointBlock(letter, text_raw)`, `ClauseBlock(number, clause_header, points)`, `ArticleBlock(doc_id, document_title, source_file, chapter, chapter_title, section, section_title, article_number, article_title, clauses, body_text)`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chunk_builder.py -k w08 -v`
Expected: FAIL — `w08_warnings` is empty (no W08 check exists yet).

- [ ] **Step 3: Implement**

In `src/lawgo_traffic/ingestion/chunk_builder.py`, immediately after the existing W04 block (after line 242, `warnings.append(f"W04: short text_raw in {ch['chunk_id']}")`), add:
```python
    # W08 — low-confidence OCR marker present in chunk text
    for ch in children:
        if "[KHÔNG RÕ:" in ch.get("text_raw", ""):
            warnings.append(f"W08: low-confidence OCR text in {ch['chunk_id']}")
```

In `scripts/build_chunks.py:69`, change:
```python
    critical_codes = {"W01", "W02", "W05"}
```
to:
```python
    critical_codes = {"W01", "W02", "W05", "W08"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chunk_builder.py -k w08 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/chunk_builder.py scripts/build_chunks.py tests/test_chunk_builder.py
git commit -m "feat: flag low-confidence OCR text as a critical W08 validation warning"
```

---

### Task 9: `extract_router.py` — `extract_all` orchestration

This is the piece that ties Tasks 4-7 together and becomes the new entrypoint for `scripts/ingest_docx.py`.

**Files:**
- Modify: `src/lawgo_traffic/ingestion/extract_router.py`
- Test: `tests/test_extract_router.py`

**Interfaces:**
- Consumes: `detect_format`, `convert_doc_to_docx` (this file, Tasks 5-6), `extract_docx_to_text`/`extract_docx_paragraphs` (`docx_extractor`, existing, unchanged), `extract_pdf_to_text` (Task 4), `extract_scanned_pdf_to_text` (Task 7), `get_doc_info` (Task 2), `settings.ocr_enabled` (`config.py`, already added)
- Produces: `extract_all(raw_dir: str, output_dir: str) -> list[str]` (consumed by `scripts/ingest_docx.py` in Task 10)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_extract_router.py`:
```python
import json
from pathlib import Path

from lawgo_traffic.ingestion.extract_router import extract_all


def test_extract_all_processes_docx_doc_and_pdf_text(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "extracted"
    raw_dir.mkdir()

    # a pdf_text file using a real registered doc_id
    (raw_dir / "Nghi-dinh-67-2023-ND-CP-baohiem-bat-buoc-xecogioi.pdf").write_bytes(
        Path("tests/fixtures/sample_law_text.pdf").read_bytes()
    )
    # a doc file using a real registered doc_id
    (raw_dir / "Luat-15-2012-QH13-XLVPHC.doc").write_bytes(
        Path("tests/fixtures/sample_law_text.doc").read_bytes()
    )

    saved = extract_all(str(raw_dir), str(out_dir))

    assert len(saved) == 2
    nd67 = json.loads((out_dir / "nd67_2023.json").read_text(encoding="utf-8"))
    assert nd67["extraction_method"] == "pdf_text"
    luat = json.loads((out_dir / "luat_xlvphc_2012.json").read_text(encoding="utf-8"))
    assert luat["extraction_method"] == "doc_to_docx"
    assert luat["source_file"] == "Luat-15-2012-QH13-XLVPHC.doc"  # original name, not converted


def test_extract_all_raises_when_ocr_needed_but_disabled(tmp_path, monkeypatch):
    from lawgo_traffic.config import settings

    monkeypatch.setattr(settings, "ocr_enabled", False)

    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "extracted"
    raw_dir.mkdir()
    (raw_dir / "Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf").write_bytes(
        Path("tests/fixtures/sample_pdf_scanned_2page.pdf").read_bytes()
    )

    with pytest.raises(RuntimeError, match="OCR_ENABLED"):
        extract_all(str(raw_dir), str(out_dir))


def test_extract_all_skips_unknown_files(tmp_path, capsys):
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "extracted"
    raw_dir.mkdir()
    (raw_dir / "unknown-file.pdf").write_bytes(
        Path("tests/fixtures/sample_law_text.pdf").read_bytes()
    )

    saved = extract_all(str(raw_dir), str(out_dir))
    assert saved == []
    assert "SKIP" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extract_router.py -v`
Expected: 3 new FAIL with `ImportError` (`extract_all` doesn't exist yet).

- [ ] **Step 3: Implement**

Add to the top of `src/lawgo_traffic/ingestion/extract_router.py` (alongside existing imports):
```python
import json

from lawgo_traffic.config import settings
from lawgo_traffic.ingestion.docx_extractor import extract_docx_paragraphs, extract_docx_to_text
from lawgo_traffic.ingestion.pdf_ocr_extractor import extract_scanned_pdf_to_text
from lawgo_traffic.ingestion.pdf_text_extractor import extract_pdf_to_text
from lawgo_traffic.ingestion.doc_id_map import get_doc_info
```

Add at the end of the file:
```python
def extract_all(raw_dir: str, output_dir: str) -> list[str]:
    """Extract every supported file in raw_dir, save JSON to output_dir.

    Mirrors docx_extractor.extract_all_docx's behaviour (skip + warn on
    files not in DOC_ID_MAP) but routes by detected format.
    """
    raw_path = Path(raw_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    candidates = sorted(
        p for p in raw_path.iterdir() if p.suffix.lower() in (".docx", ".doc", ".pdf")
    )

    for file in candidates:
        try:
            fmt = detect_format(str(file))
        except ValueError as exc:
            print(f"[SKIP] {file.name}: {exc}")
            continue

        try:
            if fmt == "docx":
                data = extract_docx_to_text(str(file))
                data["extraction_method"] = "docx"
            elif fmt == "doc":
                info = get_doc_info(str(file))  # look up BEFORE conversion renames the file
                docx_path = convert_doc_to_docx(str(file), str(out_path / "_converted"))
                paragraphs = extract_docx_paragraphs(docx_path)
                data = {
                    "source_file": file.name,
                    "doc_id": info["doc_id"],
                    "document_title": info["document_title"],
                    "paragraphs": paragraphs,
                    "extraction_method": "doc_to_docx",
                }
            elif fmt == "pdf_text":
                data = extract_pdf_to_text(str(file))
            elif fmt == "pdf_ocr":
                if not settings.ocr_enabled:
                    raise RuntimeError(
                        f"{file.name} requires OCR but OCR_ENABLED=false. "
                        "Set OCR_ENABLED=true and a valid LLM_API_KEY in .env, then re-run."
                    )
                data = extract_scanned_pdf_to_text(str(file))
            else:
                raise RuntimeError(f"detect_format returned unknown value '{fmt}' for {file}")
        except KeyError as exc:
            print(f"[SKIP] {file.name}: {exc}")
            continue

        out_file = out_path / f"{data['doc_id']}.json"
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        total = len([p for p in data["paragraphs"] if p])
        print(
            f"[OK] {file.name} → {out_file.name}  "
            f"({total} non-empty paragraphs, method={data['extraction_method']})"
        )
        saved.append(str(out_file))

    return saved
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extract_router.py -v`
Expected: all 10 PASS (5 from Task 5 + 2 from Task 6 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/lawgo_traffic/ingestion/extract_router.py tests/test_extract_router.py
git commit -m "feat: orchestrate multi-format extraction across docx/doc/pdf_text/pdf_ocr"
```

---

### Task 10: Wire into the CLI scripts

**Files:**
- Modify: `scripts/ingest_docx.py`

**Interfaces:**
- Consumes: `extract_all` from `extract_router` (Task 9)

- [ ] **Step 1: Switch the import and call site**

In `scripts/ingest_docx.py`, change:
```python
from lawgo_traffic.ingestion.docx_extractor import extract_all_docx
```
to:
```python
from lawgo_traffic.ingestion.extract_router import extract_all
```
and change:
```python
    saved = extract_all_docx(args.input, args.output)
```
to:
```python
    saved = extract_all(args.input, args.output)
```

Leave the docstring's `"""Extract text from .docx files..."""` — update it to `"""Extract text from .docx/.doc/.pdf files in raw_dir and save JSON to output_dir."""` since it now handles more than docx.

- [ ] **Step 2: Smoke-test against the 5 existing committed files only**

To confirm nothing regressed for the original 5 docx files, run against a scratch copy first (do not touch `data/extracted/` yet — Task 12 does the real run):
```bash
mkdir -p /tmp/ingest_smoke_test
cp data/raw/*.docx /tmp/ingest_smoke_test/
python scripts/ingest_docx.py --input /tmp/ingest_smoke_test --output /tmp/ingest_smoke_test_out
```
Expected: 5 `[OK]` lines, one per existing docx file, same as before this plan (the docx path is untouched code).

- [ ] **Step 3: Commit**

```bash
git add scripts/ingest_docx.py
git commit -m "feat: route ingest_docx.py through the new multi-format extract_router"
```

---

### Task 11: Add poppler-utils and LibreOffice to the Docker image

The project's stated convention is "Docker for everything — no local runtime assumptions" (`make up`/`make test` run inside the `api` container). The current `Dockerfile` only installs `curl`; `pdftotext`/`pdfinfo`/`pdfimages`/`soffice` must be added or the feature works on a developer's Mac but breaks in the actual deployed/tested environment.

**Files:**
- Modify: `Dockerfile`

**Interfaces:**
- N/A (infra only)

- [ ] **Step 1: Update the Dockerfile**

In `Dockerfile`, change:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*
```
to:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    poppler-utils \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*
```

- [ ] **Step 2: Rebuild and verify the binaries are present**

This requires Docker Desktop running locally (it was not running as of writing this plan — start it first).

Run:
```bash
docker compose build api
docker compose run --rm api bash -c "which pdftotext pdfinfo pdfimages soffice"
```
Expected: 4 paths printed, no "not found" errors.

- [ ] **Step 3: Run the full test suite inside the container**

Run: `docker compose run --rm api pytest tests/ -v`
Expected: every test from Tasks 0-10 PASSES inside the container too (not just on the host Mac).

- [ ] **Step 4: Commit**

```bash
git add Dockerfile
git commit -m "build: add poppler-utils and libreoffice-writer for multi-format ingestion"
```

---

### Task 12: Run the real ingestion on the 9 new documents

This is the only task that spends real (sub-$1) money via the user's OpenAI key and touches the committed `data/extracted/` and `data/chunks/` files. Do this only after the user has filled in `.env` with a real `LLM_API_KEY` and set `OCR_ENABLED=true` (both already scaffolded in an earlier session — confirm before running).

**Files:**
- Modify (generated data, not hand-written): `data/extracted/*.json` (9 new files), `data/chunks/parents.jsonl`, `data/chunks/children.jsonl`, `data/chunks/validation_report.json`

**Interfaces:**
- N/A — this is a pipeline run, not new code

- [ ] **Step 1: Confirm `.env` is ready**

```bash
grep -E "^(OCR_ENABLED|LLM_API_KEY)=" .env
```
Expected: `OCR_ENABLED=true` and `LLM_API_KEY=sk-...` (a real key, not the placeholder). If not, stop and ask the user to fill these in first.

- [ ] **Step 2: Run extraction on the real `data/raw/`**

```bash
python scripts/ingest_docx.py --input data/raw --output data/extracted
```
Expected: 9 new `[OK]` lines (one per new doc_id from Task 2's table), in addition to the 5 existing ones. The `tt72_2024_bca` line should show `method=pdf_ocr`. Two files are expected to be skipped with `[SKIP]` — the two `*-PhuLuc.pdf` appendix files (not in `DOC_ID_MAP` by design, per spec 04 §9 — out of scope).

- [ ] **Step 3: Rebuild chunks and validation report**

```bash
python scripts/build_chunks.py --input data/extracted --output data/chunks
```
Expected: parent/child counts increase from the spec-01 baseline (298 parents / 3151 children); `validation_report.json` now has 14 entries. Check for any `[CRITICAL]` lines printed — `W08` entries (if any) point to OCR text needing manual review against the original scanned pages in `data/extracted/_ocr_debug/tt72_2024_bca_page_*.txt`.

- [ ] **Step 4: Spot-check the known PDF line-wrap limitation**

Per spec 04 §1, long article titles in PDF-sourced documents can spill into `body_text` instead of staying in `article_title`, because `legal_parser.py` was deliberately left unchanged. Manually inspect 2-3 parent chunks from a new PDF-sourced doc_id (e.g. `tt35_2024_bgtvt`) in `data/chunks/parents.jsonl`:
```bash
grep '"doc_id": "tt35_2024_bgtvt"' data/chunks/parents.jsonl | head -3
```
Confirm the full title text is present *somewhere* in the chunk (even if at the end of `text` rather than in `article_title`) — this is the accepted, documented limitation, not a bug to fix here.

- [ ] **Step 5: Commit the regenerated data**

```bash
git add data/extracted data/chunks
git commit -m "data: ingest 9 new traffic-law documents (Luật XLVPHC, GPLX, đăng kiểm, bảo hiểm, TNGT, biển báo)"
```
