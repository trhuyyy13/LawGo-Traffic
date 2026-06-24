import pytest

from lawgo_traffic.ingestion.doc_id_map import get_doc_info


@pytest.mark.parametrize(
    "filename,expected_doc_id",
    [
        ("Luat-15-2012-QH13-XLVPHC.doc", "luat_xlvphc_2012"),
        ("Luat-67-2020-QH14-XLVPHC-suadoi.pdf", "luat_xlvphc_2020"),
        ("Luat-88-2025-QH15-XLVPHC-suadoi.pdf", "luat_xlvphc_2025"),
        ("Thong-tu-35-2024-TT-BGTVT-daotao-GPLX.pdf", "tt35_2024_bgtvt"),
        ("Thong-tu-12-2025-TT-BCA-sathach-capGPLX.pdf", "tt12_2025_bca"),
        ("Thong-tu-47-2024-TT-BGTVT-kiemdinh-xecogioi.pdf", "tt47_2024_bgtvt"),
        ("Nghi-dinh-67-2023-ND-CP-baohiem-bat-buoc-xecogioi.pdf", "nd67_2023"),
        ("Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf", "tt72_2024_bca"),
        ("Thong-tu-51-2024-TT-BGTVT-QCVN41-2024-baohieuduongbo.pdf", "tt51_2024_bgtvt"),
    ],
)
def test_new_documents_resolve(filename, expected_doc_id):
    info = get_doc_info(filename)
    assert info["doc_id"] == expected_doc_id
    assert info["document_title"]  # non-empty
