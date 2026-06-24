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
