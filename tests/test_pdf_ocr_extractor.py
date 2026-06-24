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
