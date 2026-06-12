import re
import unicodedata


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^a-z0-9\s_]", "", text)
    return re.sub(r"\s+", "_", text.strip())


def make_article_id(doc_id: str, article_number: str) -> str:
    return f"{doc_id}_dieu_{article_number}"


def make_clause_id(doc_id: str, article_number: str, clause_number: str) -> str:
    return f"{doc_id}_dieu_{article_number}_khoan_{clause_number}"


def make_point_id(doc_id: str, article_number: str, clause_number: str, point_letter: str) -> str:
    return f"{doc_id}_dieu_{article_number}_khoan_{clause_number}_diem_{point_letter}"
