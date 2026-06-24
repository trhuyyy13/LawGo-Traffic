import pytest

from lawgo_traffic.ingestion.chunk_builder import build_all_chunks, build_validation_report
from lawgo_traffic.ingestion.legal_parser import ArticleBlock, ClauseBlock, PointBlock


def test_child_has_parent_id():
    pytest.skip("Not implemented yet")


def test_child_has_legal_path():
    pytest.skip("Not implemented yet")


def test_no_duplicate_chunk_ids():
    pytest.skip("Not implemented yet")


def test_text_for_search_contains_legal_path():
    pytest.skip("Not implemented yet")


def test_low_confidence_ocr_marker_produces_w08_warning():
    article = ArticleBlock(
        doc_id="tt72_2024_bca",
        document_title="Thông tư 72/2024/TT-BCA",
        source_file="Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf",
        chapter=None,
        chapter_title=None,
        section=None,
        section_title=None,
        article_number="1",
        article_title="Phạm vi điều chỉnh",
    )
    article.clauses = [
        ClauseBlock(number="1", clause_header="Khoản 1"),
    ]
    article.clauses[0].points = [
        PointBlock(letter="a", text_raw="Nội dung rõ ràng"),
        PointBlock(letter="b", text_raw="Nội dung [KHÔNG RÕ: mờ chữ] không chắc"),
    ]

    children = [
        {"chunk_id": "tt72_2024_bca_dieu_1_khoan_1_diem_a", "chunk_type": "POINT",
         "text_raw": "Nội dung rõ ràng", "clause_header": "Khoản 1"},
        {"chunk_id": "tt72_2024_bca_dieu_1_khoan_1_diem_b", "chunk_type": "POINT",
         "text_raw": "Nội dung [KHÔNG RÕ: mờ chữ] không chắc", "clause_header": "Khoản 1"},
    ]

    report = build_validation_report(
        "Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf",
        "tt72_2024_bca",
        [article],
        parents=[],
        children=children,
    )

    w08_warnings = [w for w in report["warnings"] if w.startswith("W08")]
    assert len(w08_warnings) == 1
    assert "tt72_2024_bca_dieu_1_khoan_1_diem_b" in w08_warnings[0]
