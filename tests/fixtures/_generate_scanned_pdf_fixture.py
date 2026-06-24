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
