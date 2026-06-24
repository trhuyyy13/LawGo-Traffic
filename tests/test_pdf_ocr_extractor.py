from pathlib import Path
from unittest.mock import MagicMock

from lawgo_traffic.ingestion import pdf_ocr_extractor
from lawgo_traffic.ingestion.pdf_ocr_extractor import (
    _extract_page_images,
    _ocr_page,
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


def _make_mock_openai_client(response_text: str = "Điều 1. Nội dung") -> MagicMock:
    """Build a fake OpenAI client whose chat.completions.create() returns a
    minimal, valid-shaped response object, mirroring the real SDK response.
    """
    client = MagicMock()
    message = MagicMock()
    message.content = response_text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create.return_value = response
    return client


def test_ocr_page_uses_image_jpeg_mime_type_for_jpg_extension(tmp_path):
    """pdfimages -all extracts page images with a literal .jpg extension.

    OpenAI's vision API only accepts the MIME subtype "jpeg", not "jpg" —
    a data URL of "data:image/jpg;..." is rejected with 400 invalid_image_format.
    This test exercises the real `_ocr_page` function (not a stand-in) against
    a real file with a `.jpg` suffix, and inspects the exact `messages` payload
    passed to `client.chat.completions.create` to confirm the MIME type is
    normalized to "jpeg".
    """
    image_path = tmp_path / "page-000.jpg"
    # Content is irrelevant — the bug is purely in extension-to-MIME-type
    # string mapping, not actual image decoding/validity.
    image_path.write_bytes(b"not a real jpeg, just bytes")

    client = _make_mock_openai_client()

    _ocr_page(client, str(image_path))

    client.chat.completions.create.assert_called_once()
    _, kwargs = client.chat.completions.create.call_args
    messages = kwargs["messages"]
    image_content = next(
        part for part in messages[0]["content"] if part["type"] == "image_url"
    )
    url = image_content["image_url"]["url"]

    assert "image/jpeg" in url
    assert "image/jpg;" not in url
