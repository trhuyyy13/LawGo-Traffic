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
    "Luat-15-2012-QH13-XLVPHC.doc": {
        "doc_id": "luat_xlvphc_2012",
        "document_title": "Luật Xử lý vi phạm hành chính 15/2012/QH13",
    },
    "Luat-67-2020-QH14-XLVPHC-suadoi.pdf": {
        "doc_id": "luat_xlvphc_2020",
        "document_title": "Luật sửa đổi, bổ sung một số điều của Luật Xử lý vi phạm hành chính 67/2020/QH14",
    },
    "Luat-88-2025-QH15-XLVPHC-suadoi.pdf": {
        "doc_id": "luat_xlvphc_2025",
        "document_title": "Luật sửa đổi, bổ sung một số điều của Luật Xử lý vi phạm hành chính 88/2025/QH15",
    },
    "Thong-tu-35-2024-TT-BGTVT-daotao-GPLX.pdf": {
        "doc_id": "tt35_2024_bgtvt",
        "document_title": "Thông tư 35/2024/TT-BGTVT",
    },
    "Thong-tu-12-2025-TT-BCA-sathach-capGPLX.pdf": {
        "doc_id": "tt12_2025_bca",
        "document_title": "Thông tư 12/2025/TT-BCA",
    },
    "Thong-tu-47-2024-TT-BGTVT-kiemdinh-xecogioi.pdf": {
        "doc_id": "tt47_2024_bgtvt",
        "document_title": "Thông tư 47/2024/TT-BGTVT",
    },
    "Nghi-dinh-67-2023-ND-CP-baohiem-bat-buoc-xecogioi.pdf": {
        "doc_id": "nd67_2023",
        "document_title": "Nghị định 67/2023/NĐ-CP",
    },
    "Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf": {
        "doc_id": "tt72_2024_bca",
        "document_title": "Thông tư 72/2024/TT-BCA",
    },
    "Thong-tu-51-2024-TT-BGTVT-QCVN41-2024-baohieuduongbo.pdf": {
        "doc_id": "tt51_2024_bgtvt",
        "document_title": "Thông tư 51/2024/TT-BGTVT",
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
