import pytest

from lawgo_traffic.ingestion.docx_extractor import extract_docx_paragraphs
from lawgo_traffic.ingestion.extract_router import detect_format, convert_doc_to_docx

TEXT_PDF = "tests/fixtures/sample_law_text.pdf"
SCANNED_PDF = "tests/fixtures/sample_pdf_scanned_2page.pdf"
DOC_FIXTURE = "tests/fixtures/sample_law_text.doc"


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


def test_convert_doc_to_docx_produces_readable_docx(tmp_path):
    out_path = convert_doc_to_docx(DOC_FIXTURE, str(tmp_path))
    assert out_path.endswith(".docx")

    paragraphs = extract_docx_paragraphs(out_path)
    assert any("Điều 7" in p for p in paragraphs)


def test_convert_doc_to_docx_missing_binary_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", "/nonexistent")
    with pytest.raises(RuntimeError, match="soffice not found"):
        convert_doc_to_docx(DOC_FIXTURE, str(tmp_path))
