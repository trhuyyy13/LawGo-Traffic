import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lawgo_traffic.ingestion import pdf_ocr_extractor
from lawgo_traffic.ingestion.pdf_ocr_extractor import (
    _extract_page_images,
    _ocr_page,
    _page_number_sort_key,
    extract_scanned_pdf_to_text,
)

SCANNED_FIXTURE = "tests/fixtures/sample_pdf_scanned_2page.pdf"
SCANNED_FIXTURE_11PAGE = "tests/fixtures/sample_pdf_scanned_11page.pdf"


def test_extract_page_images_returns_one_image_per_page(tmp_path):
    images = _extract_page_images(SCANNED_FIXTURE, str(tmp_path))
    assert len(images) == 2
    for img in images:
        assert Path(img).exists()


def test_extract_page_images_produces_real_standalone_png_files(tmp_path):
    """_extract_page_images must rasterize via pdftoppm, not extract the raw
    embedded stream via pdfimages. pdfimages -all on some real corpus
    documents extracts JBIG2/CCITT-G4 fax streams that are not standalone
    decodable images (OpenAI's vision API rejects them with
    invalid_image_format), whereas pdftoppm always produces a real,
    independently decodable PNG regardless of the source encoding. We
    confirm this with the actual `file` command rather than just trusting
    the extension.
    """
    images = _extract_page_images(SCANNED_FIXTURE, str(tmp_path))
    for img in images:
        assert img.endswith(".png")
        result = subprocess.run(["file", img], capture_output=True, text=True, check=True)
        assert "PNG image data" in result.stdout


def test_extract_page_images_orders_pages_numerically_not_lexicographically(tmp_path):
    """Regression test for the page-10-before-page-2 ordering bug.

    pdftoppm names output "<prefix>-<n>.png" with n 1-indexed; whether n is
    zero-padded is poppler-version-dependent. A plain lexicographic string
    sort over filenames like "page-1.png".."page-11.png" (no padding) would
    order page 10 and 11 before page 2 — silently scrambling page order for
    any 10+ page document. This test uses a real 11-page fixture (each page
    rendered as a distinct grayscale shade: page N -> shade N*20) and decodes
    each returned image's pixel value to independently verify TRUE page
    order, regardless of what zero-padding this machine's poppler happens to
    produce.
    """
    from PIL import Image

    images = _extract_page_images(SCANNED_FIXTURE_11PAGE, str(tmp_path))
    assert len(images) == 11

    shades = [Image.open(img).getpixel((5, 5))[0] for img in images]
    expected_shades = [i * 20 for i in range(11)]
    assert shades == expected_shades


@pytest.mark.parametrize(
    "filenames,expected_order",
    [
        (
            # Unpadded pdftoppm naming (older poppler / small page counts):
            # a plain string sort would put "-10" and "-11" before "-2".
            [f"page-{n}.png" for n in [1, 10, 11, 2, 3, 4, 5, 6, 7, 8, 9]],
            [f"page-{n}.png" for n in range(1, 12)],
        ),
        (
            # Zero-padded pdftoppm naming (poppler pads to fit page count).
            [f"page-{n:02d}.png" for n in [1, 10, 11, 2, 3]],
            ["page-01.png", "page-02.png", "page-03.png", "page-10.png", "page-11.png"],
        ),
    ],
)
def test_page_number_sort_key_orders_numerically(tmp_path, filenames, expected_order):
    """Unit-level proof that the sort key is numeric, independent of
    whatever zero-padding the locally installed poppler version happens to
    produce. Without this fix (plain `sorted(paths)` on filenames), the
    unpadded case would sort to
    ['page-1.png', 'page-10.png', 'page-11.png', 'page-2.png', ...] — wrong.
    """
    paths = [Path(tmp_path) / name for name in filenames]
    ordered = sorted(paths, key=_page_number_sort_key)
    assert [p.name for p in ordered] == expected_order


def test_extract_page_images_orders_unpadded_filenames_numerically(monkeypatch, tmp_path):
    """Exercises the real _extract_page_images call site (not just the
    _page_number_sort_key helper in isolation) against the exact failure
    mode of an older/unpadded poppler version, by mocking subprocess.run to
    write unpadded "page-<n>.png" files directly into tmp_dir instead of
    really invoking pdftoppm. This guarantees the regression is caught even
    on a machine whose installed poppler always zero-pads — where a real
    end-to-end pdftoppm run would never produce unpadded names and so could
    never exercise this bug.
    """
    def fake_run(cmd, **kwargs):
        # cmd = ["pdftoppm", "-png", "-r", "200", input_path, prefix]
        prefix = cmd[-1]
        for n in [1, 10, 11, 2, 3, 4, 5, 6, 7, 8, 9]:
            Path(f"{prefix}-{n}.png").write_bytes(b"")
        return MagicMock(returncode=0, stderr="")

    monkeypatch.setattr(pdf_ocr_extractor.subprocess, "run", fake_run)

    images = _extract_page_images("irrelevant.pdf", str(tmp_path))

    assert [Path(p).name for p in images] == [f"page-{n}.png" for n in range(1, 12)]


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
