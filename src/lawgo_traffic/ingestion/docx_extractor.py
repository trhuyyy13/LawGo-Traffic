import json
from pathlib import Path

from docx import Document

from lawgo_traffic.ingestion.doc_id_map import get_doc_info
from lawgo_traffic.utils.text_normalizer import normalize_paragraph


def extract_docx_paragraphs(input_path: str) -> list[str]:
    """Return normalized paragraph texts from a .docx file, preserving order.

    Empty paragraphs (after normalization) are included as empty strings so the
    caller can use index-based peeking when needed.  Callers that don't need
    empty lines should filter them out themselves.
    """
    doc = Document(input_path)
    return [normalize_paragraph(p.text) for p in doc.paragraphs]


def extract_docx_to_text(input_path: str) -> dict:
    """Extract a single .docx file and return a structured dict.

    Returns:
        {
            "source_file": "168.2024.NĐ.CP.docx",
            "doc_id": "nd168_2024",
            "document_title": "Nghị định 168/2024/NĐ-CP",
            "paragraphs": ["para1", "para2", ...]   # normalized, includes empty lines
        }
    """
    info = get_doc_info(input_path)
    paragraphs = extract_docx_paragraphs(input_path)
    return {
        "source_file": Path(input_path).name,
        "doc_id": info["doc_id"],
        "document_title": info["document_title"],
        "paragraphs": paragraphs,
    }


def extract_all_docx(raw_dir: str, output_dir: str) -> list[str]:
    """Extract all .docx files in raw_dir, save JSON to output_dir.

    Returns list of paths to the saved JSON files.
    Skips files whose basename is not in DOC_ID_MAP (prints a warning).
    """
    raw_path = Path(raw_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for docx_file in sorted(raw_path.glob("*.docx")):
        try:
            data = extract_docx_to_text(str(docx_file))
        except KeyError as exc:
            print(f"[SKIP] {docx_file.name}: {exc}")
            continue

        out_file = out_path / f"{data['doc_id']}.json"
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        total = len([p for p in data["paragraphs"] if p])
        print(f"[OK] {docx_file.name} → {out_file.name}  ({total} non-empty paragraphs)")
        saved.append(str(out_file))

    return saved
