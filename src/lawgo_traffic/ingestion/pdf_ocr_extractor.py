import base64
import re
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


def _page_number_sort_key(path: Path) -> int:
    """Extract the page number from a pdftoppm-generated filename for sorting.

    pdftoppm names output "<prefix>-<n>.png" where <n> is 1-indexed and is
    zero-padded to the width needed for the document's total page count
    *in some poppler versions*, but NOT in others (e.g. plain "-1", "-2", ...,
    "-10", "-11" with no padding). A plain lexicographic string sort silently
    misorders page 10 before page 2 whenever padding is absent, so we must
    always sort by the parsed integer page number rather than the string.
    """
    match = re.search(r"-(\d+)\.[^.]+$", path.name)
    if not match:
        raise RuntimeError(f"could not parse page number from filename: {path.name}")
    return int(match.group(1))


def _extract_page_images(input_path: str, tmp_dir: str) -> list[str]:
    """Rasterize every page to a standalone PNG via pdftoppm.

    We deliberately rasterize with pdftoppm rather than extracting the
    embedded image stream with pdfimages: some scanned documents in this
    corpus store their pages as raw JBIG2 or CCITT-G4 fax-encoded streams,
    which pdfimages -all extracts verbatim (".jb2e", ".ccitt"+".params") —
    not standalone decodable image files, and OpenAI's vision API rejects
    them with invalid_image_format. pdftoppm always rasterizes to a real
    PNG regardless of the source encoding (JPEG, JBIG2, CCITT, anything),
    at the cost of being slower and producing larger files.

    Returns image paths sorted in page order. pdftoppm's "<prefix>-<n>.png"
    numbering is 1-indexed and its zero-padding width is poppler-version-
    dependent (some versions pad to the document's page count, others don't
    pad at all), so page order is determined by parsing and sorting the
    numeric page number rather than relying on a plain string sort.
    """
    prefix = str(Path(tmp_dir) / "page")
    try:
        result = subprocess.run(
            ["pdftoppm", "-png", "-r", "200", input_path, prefix],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdftoppm not found — install poppler-utils (`brew install poppler` "
            "on macOS, `apt-get install poppler-utils` in Docker)"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed on {input_path}: {result.stderr.strip()}")

    images = sorted(Path(tmp_dir).glob("page-*.png"), key=_page_number_sort_key)
    if not images:
        raise RuntimeError(f"pdftoppm produced no images for {input_path}")
    return [str(p) for p in images]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def _ocr_page(client: OpenAI, image_path: str) -> str:
    """Call the configured OpenAI vision model on a single page image."""
    image_bytes = Path(image_path).read_bytes()
    b64 = base64.b64encode(image_bytes).decode("ascii")
    ext = Path(image_path).suffix.lstrip(".").lower() or "jpeg"
    if ext == "jpg":
        ext = "jpeg"

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
