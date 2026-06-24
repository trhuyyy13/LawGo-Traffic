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
