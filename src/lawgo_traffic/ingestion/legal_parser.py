import re
from dataclasses import dataclass, field

CHAPTER_PATTERN = re.compile(r"^(Chương|CHƯƠNG)\s+[IVXLCDM]+", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(Mục|MỤC)\s+\d+", re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"^Điều\s+(\d+[a-zA-Z]?)\.")
CLAUSE_PATTERN = re.compile(r"^(\d+)\.")
POINT_PATTERN = re.compile(r"^([a-zđ])\)")


@dataclass
class LegalUnit:
    doc_id: str
    document_title: str | None = None
    chapter: str | None = None
    section: str | None = None
    article: str | None = None
    article_title: str | None = None
    clause: str | None = None
    point: str | None = None
    text: str = ""


def parse_legal_document(text: str, doc_id: str, document_title: str | None = None) -> list[LegalUnit]:
    """Parse Vietnamese legal document text into LegalUnit list."""
    # TODO: implement state-machine paragraph parser
    raise NotImplementedError
