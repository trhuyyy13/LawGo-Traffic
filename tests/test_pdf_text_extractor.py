from lawgo_traffic.ingestion.pdf_text_extractor import _clean_pdf_lines


def test_strips_lone_page_number_lines():
    raw = "Điều 1. Nội dung\n1\nKhoản 1 tiếp tục"
    lines = _clean_pdf_lines(raw)
    assert "1" not in lines
    assert "Điều 1. Nội dung" in lines
    assert "Khoản 1 tiếp tục" in lines


def test_strips_repeated_header_across_pages():
    raw = (
        "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐiều 1. Nội dung trang 1\n"
        "\f"
        "CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐiều 2. Nội dung trang 2"
    )
    lines = _clean_pdf_lines(raw)
    assert lines.count("CỘNG HOÀ XÃ HỘI CHỦ NGHĨA VIỆT NAM") == 0
    assert "Điều 1. Nội dung trang 1" in lines
    assert "Điều 2. Nội dung trang 2" in lines


def test_keeps_line_that_only_appears_once():
    raw = "Điều 1. Tiêu đề riêng\nNội dung\n\fĐiều 2. Tiêu đề khác\nNội dung khác"
    lines = _clean_pdf_lines(raw)
    assert "Điều 1. Tiêu đề riêng" in lines
    assert "Điều 2. Tiêu đề khác" in lines
