import json
from pathlib import Path

import pytest

from lawgo_traffic.ingestion.docx_extractor import extract_docx_paragraphs
from lawgo_traffic.ingestion.extract_router import detect_format, convert_doc_to_docx, extract_all

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
