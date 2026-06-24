"""Regenerate tests/fixtures/sample_pdf_scanned_11page.pdf.

Run manually if the fixture needs to change:
    python tests/fixtures/_generate_scanned_pdf_fixture_11page.py
Produces an 11-page PDF with embedded images and NO text layer. Each page is
filled with a distinct grayscale shade (page N -> shade N*20) so that, after
running pdftoppm on the fixture, a test can independently verify TRUE page
order (not just that filenames happen to already be in some order) — this is
needed to catch a lexicographic-vs-numeric filename sort bug for 10+ pages,
which a 2-page fixture cannot exercise (single digits can't misorder).
"""
from pathlib import Path

from PIL import Image

OUT_PATH = Path(__file__).parent / "sample_pdf_scanned_11page.pdf"
NUM_PAGES = 11


def main() -> None:
    pages = [
        Image.new("RGB", (200, 260), color=(shade, shade, shade))
        for shade in (i * 20 for i in range(NUM_PAGES))
    ]
    pages[0].save(OUT_PATH, "PDF", save_all=True, append_images=pages[1:])
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
