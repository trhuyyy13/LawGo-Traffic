import unicodedata
from pathlib import Path

DOC_ID_MAP: dict[str, dict[str, str]] = {
    "168.2024.NĐ.CP.docx": {
        "doc_id": "nd168_2024",
        "document_title": "Nghị định 168/2024/NĐ-CP",
    },
    "36:2024:QH15_luattrậttự.docx": {
        "doc_id": "luat36_2024",
        "document_title": "Luật Trật tự, An toàn Giao thông Đường bộ 36/2024/QH15",
    },
    "Luật-35-2024-QH15.docx": {
        "doc_id": "luat35_2024",
        "document_title": "Luật Đường bộ 35/2024/QH15",
    },
    "24_2023_TT-BCA_m_559088.docx": {
        "doc_id": "tt24_2023_bca",
        "document_title": "Thông tư 24/2023/TT-BCA",
    },
    "Nghị-định-336-2025-NĐ-CP.docx": {
        "doc_id": "nd336_2025",
        "document_title": "Nghị định 336/2025/NĐ-CP",
    },
}


def get_doc_info(filepath: str) -> dict[str, str]:
    """Return {doc_id, document_title} for a given .docx filepath.

    Raises KeyError if the filename is not in DOC_ID_MAP.
    """
    # macOS HFS+ stores filenames in NFD; DOC_ID_MAP keys are NFC.
    basename = unicodedata.normalize("NFC", Path(filepath).name)
    if basename not in DOC_ID_MAP:
        raise KeyError(
            f"Unknown source file '{basename}'. "
            f"Add it to DOC_ID_MAP in doc_id_map.py. "
            f"Known files: {list(DOC_ID_MAP.keys())}"
        )
    return DOC_ID_MAP[basename]
