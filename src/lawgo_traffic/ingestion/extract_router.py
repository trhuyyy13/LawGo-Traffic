import json
import subprocess
from pathlib import Path

from lawgo_traffic.config import settings
from lawgo_traffic.ingestion.doc_id_map import get_doc_info
from lawgo_traffic.ingestion.docx_extractor import extract_docx_paragraphs, extract_docx_to_text
from lawgo_traffic.ingestion.pdf_ocr_extractor import extract_scanned_pdf_to_text
from lawgo_traffic.ingestion.pdf_text_extractor import extract_pdf_to_text, run_pdftotext

PDF_OCR_AVG_CHARS_PER_PAGE_THRESHOLD = 20


def _pdf_page_count(input_path: str) -> int:
    try:
        result = subprocess.run(
            ["pdfinfo", input_path], capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdfinfo not found — install poppler-utils (`brew install poppler` "
            "on macOS, `apt-get install poppler-utils` in Docker)"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"pdfinfo failed on {input_path}: {result.stderr.strip()}")
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"pdfinfo output for {input_path} has no 'Pages:' line")


def detect_format(filepath: str) -> str:
    """Return 'docx' | 'doc' | 'pdf_text' | 'pdf_ocr' for a raw input file."""
    suffix = Path(filepath).suffix.lower()
    if suffix == ".docx":
        return "docx"
    if suffix == ".doc":
        return "doc"
    if suffix == ".pdf":
        raw_text = run_pdftotext(filepath)
        pages = _pdf_page_count(filepath)
        avg_chars = len(raw_text.strip()) / pages if pages else 0
        return "pdf_ocr" if avg_chars < PDF_OCR_AVG_CHARS_PER_PAGE_THRESHOLD else "pdf_text"
    raise ValueError(f"Unsupported file extension '{suffix}' for {filepath}")


def convert_doc_to_docx(input_path: str, output_dir: str) -> str:
    """Convert a legacy .doc file to .docx via headless LibreOffice.

    Returns the path to the converted .docx file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "docx", "--outdir", output_dir, input_path],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "soffice not found — install LibreOffice "
            "(`brew install --cask libreoffice` on macOS, "
            "`apt-get install libreoffice-writer` in Docker)"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(f"soffice conversion failed on {input_path}: {result.stderr.strip()}")

    converted = Path(output_dir) / (Path(input_path).stem + ".docx")
    if not converted.exists():
        raise RuntimeError(f"soffice did not produce expected output: {converted}")
    return str(converted)


def extract_all(raw_dir: str, output_dir: str) -> list[str]:
    """Extract every supported file in raw_dir, save JSON to output_dir.

    Mirrors docx_extractor.extract_all_docx's behaviour (skip + warn on
    files not in DOC_ID_MAP) but routes by detected format.
    """
    raw_path = Path(raw_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    candidates = sorted(
        p for p in raw_path.iterdir() if p.suffix.lower() in (".docx", ".doc", ".pdf")
    )

    for file in candidates:
        try:
            fmt = detect_format(str(file))
        except ValueError as exc:
            print(f"[SKIP] {file.name}: {exc}")
            continue

        try:
            if fmt == "docx":
                data = extract_docx_to_text(str(file))
                data["extraction_method"] = "docx"
            elif fmt == "doc":
                info = get_doc_info(str(file))  # look up BEFORE conversion renames the file
                docx_path = convert_doc_to_docx(str(file), str(out_path / "_converted"))
                paragraphs = extract_docx_paragraphs(docx_path)
                data = {
                    "source_file": file.name,
                    "doc_id": info["doc_id"],
                    "document_title": info["document_title"],
                    "paragraphs": paragraphs,
                    "extraction_method": "doc_to_docx",
                }
            elif fmt == "pdf_text":
                data = extract_pdf_to_text(str(file))
            elif fmt == "pdf_ocr":
                if not settings.ocr_enabled:
                    raise RuntimeError(
                        f"{file.name} requires OCR but OCR_ENABLED=false. "
                        "Set OCR_ENABLED=true and a valid LLM_API_KEY in .env, then re-run."
                    )
                data = extract_scanned_pdf_to_text(str(file))
            else:
                raise RuntimeError(f"detect_format returned unknown value '{fmt}' for {file}")
        except KeyError as exc:
            print(f"[SKIP] {file.name}: {exc}")
            continue

        out_file = out_path / f"{data['doc_id']}.json"
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        total = len([p for p in data["paragraphs"] if p])
        print(
            f"[OK] {file.name} → {out_file.name}  "
            f"({total} non-empty paragraphs, method={data['extraction_method']})"
        )
        saved.append(str(out_file))

    return saved
