import re
from dataclasses import dataclass, field

from lawgo_traffic.utils.text_normalizer import normalize_paragraph

# ---------------------------------------------------------------------------
# Regex patterns — validated against all 5 real .docx files
# ---------------------------------------------------------------------------

# "Chương I", "Chương II", "CHƯƠNG IV" — anchored with $ to avoid matching
# lines that start with a chapter keyword but have more content.
CHAPTER_PATTERN = re.compile(r"^(Chương|CHƯƠNG)\s+[IVXLCDM]+$", re.IGNORECASE)

# "Mục 1", "Mục 2" — anchored with $ for the same reason.
SECTION_PATTERN = re.compile(r"^(Mục|MỤC)\s+\d+$", re.IGNORECASE)

# "Điều 7. Article title here" — group 1 = number, group 2 = title.
# Title always on the same line as "Điều N." — confirmed across all 5 files.
ARTICLE_PATTERN = re.compile(r"^Điều\s+(\d+[a-zA-Z]?)\.\s*(.+)")

# "1. Text..." — 1-2 digits + period + mandatory space.
# The mandatory space prevents matching "200.000" or "168/2024/NĐ-CP".
# Max clause number seen in real files: 14 (NĐ168 Điều 6).
CLAUSE_PATTERN = re.compile(r"^(\d{1,2})\.\s+(.+)")

# "a) Text...", "đ) Text..." — single lowercase letter (incl. đ) + closing paren.
POINT_PATTERN = re.compile(r"^([a-zđ])\)\s*(.+)")

_STRUCTURAL_PATTERNS = (CHAPTER_PATTERN, SECTION_PATTERN, ARTICLE_PATTERN, CLAUSE_PATTERN, POINT_PATTERN)


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class PointBlock:
    letter: str
    text_raw: str


@dataclass
class ClauseBlock:
    number: str
    clause_header: str            # full text of the clause line (e.g. "Phạt tiền từ...")
    points: list[PointBlock] = field(default_factory=list)


@dataclass
class ArticleBlock:
    doc_id: str
    document_title: str
    source_file: str
    chapter: str | None
    chapter_title: str | None
    section: str | None
    section_title: str | None
    article_number: str           # "7", "35a"
    article_title: str
    clauses: list[ClauseBlock] = field(default_factory=list)
    body_text: str = ""           # direct text when article has no clauses


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class _LegalDocParser:
    def __init__(self, doc_id: str, document_title: str, source_file: str) -> None:
        self.doc_id = doc_id
        self.document_title = document_title
        self.source_file = source_file

        self.started = False
        self.current_chapter: str | None = None
        self.current_chapter_title: str | None = None
        self.current_section: str | None = None
        self.current_section_title: str | None = None

        self.articles: list[ArticleBlock] = []
        self.current_article: ArticleBlock | None = None
        self.current_clause: ClauseBlock | None = None
        self.current_point: PointBlock | None = None
        self.current_level: str | None = None  # 'article' | 'clause' | 'point'

        self.warnings: list[str] = []

    # -----------------------------------------------------------------------
    # Flush helpers — called from deepest to shallowest
    # -----------------------------------------------------------------------

    def _flush_point(self) -> None:
        if self.current_point is not None and self.current_clause is not None:
            self.current_clause.points.append(self.current_point)
            self.current_point = None

    def _flush_clause(self) -> None:
        self._flush_point()
        if self.current_clause is not None and self.current_article is not None:
            self.current_article.clauses.append(self.current_clause)
            self.current_clause = None

    def _flush_article(self) -> None:
        self._flush_clause()
        if self.current_article is not None:
            self.articles.append(self.current_article)
            self.current_article = None

    # -----------------------------------------------------------------------
    # Peek helper — checks if a paragraph looks structural
    # -----------------------------------------------------------------------

    @staticmethod
    def _is_structural(text: str) -> bool:
        return any(pat.match(text) for pat in _STRUCTURAL_PATTERNS)

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------

    def process(self, paragraphs: list[str]) -> list[ArticleBlock]:
        i = 0
        while i < len(paragraphs):
            p = paragraphs[i]  # already normalized by extract_docx_paragraphs
            if not p:
                i += 1
                continue

            # --- preamble skip ---
            if not self.started:
                if CHAPTER_PATTERN.match(p) or ARTICLE_PATTERN.match(p):
                    self.started = True
                    # fall through to normal processing below
                else:
                    i += 1
                    continue

            # --- try each pattern in priority order ---

            m = CHAPTER_PATTERN.match(p)
            if m:
                self._flush_article()
                self.current_chapter = p
                self.current_chapter_title = None
                self.current_section = None
                self.current_section_title = None
                self.current_level = None
                # peek N+1 for chapter title
                if i + 1 < len(paragraphs):
                    next_p = paragraphs[i + 1]
                    if next_p and not self._is_structural(next_p):
                        self.current_chapter_title = next_p
                        i += 2
                        continue
                i += 1
                continue

            m = SECTION_PATTERN.match(p)
            if m:
                self._flush_article()
                self.current_section = p
                self.current_section_title = None
                self.current_level = None
                # peek N+1 for section title
                if i + 1 < len(paragraphs):
                    next_p = paragraphs[i + 1]
                    if next_p and not self._is_structural(next_p):
                        self.current_section_title = next_p
                        i += 2
                        continue
                i += 1
                continue

            m = ARTICLE_PATTERN.match(p)
            if m:
                self._flush_article()
                self.current_article = ArticleBlock(
                    doc_id=self.doc_id,
                    document_title=self.document_title,
                    source_file=self.source_file,
                    chapter=self.current_chapter,
                    chapter_title=self.current_chapter_title,
                    section=self.current_section,
                    section_title=self.current_section_title,
                    article_number=m.group(1),
                    article_title=m.group(2).strip(),
                )
                self.current_clause = None
                self.current_point = None
                self.current_level = "article"
                i += 1
                continue

            m = CLAUSE_PATTERN.match(p)
            if m:
                if self.current_article is None:
                    self.warnings.append(f"W01: orphan clause at para {i}: '{p[:60]}'")
                    i += 1
                    continue
                self._flush_clause()
                self.current_clause = ClauseBlock(
                    number=m.group(1),
                    clause_header=m.group(2).strip(),
                )
                self.current_point = None
                self.current_level = "clause"
                i += 1
                continue

            m = POINT_PATTERN.match(p)
            if m:
                if self.current_clause is None:
                    self.warnings.append(f"W02: orphan point at para {i}: '{p[:60]}'")
                    i += 1
                    continue
                self._flush_point()
                self.current_point = PointBlock(
                    letter=m.group(1),
                    text_raw=m.group(2).strip(),
                )
                self.current_level = "point"
                i += 1
                continue

            # --- continuation text (no pattern matched) ---
            if self.current_level == "point" and self.current_point is not None:
                self.current_point.text_raw += " " + p
            elif self.current_level == "clause" and self.current_clause is not None:
                self.current_clause.clause_header += " " + p
            elif self.current_level == "article" and self.current_article is not None:
                if self.current_article.body_text:
                    self.current_article.body_text += " " + p
                else:
                    self.current_article.body_text = p
            # else: still in preamble or between sections — discard

            i += 1

        # flush whatever remains
        self._flush_article()
        return self.articles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_legal_document(
    paragraphs: list[str],
    doc_id: str,
    document_title: str,
    source_file: str,
) -> list[ArticleBlock]:
    """Parse a list of normalized paragraphs into a list of ArticleBlock.

    Each ArticleBlock contains the full nested structure:
      Article → Clauses → Points

    Args:
        paragraphs:      Output of extract_docx_paragraphs() (already normalized).
        doc_id:          Stable identifier (e.g. "nd168_2024").
        document_title:  Human-readable title (e.g. "Nghị định 168/2024/NĐ-CP").
        source_file:     Original filename (e.g. "168.2024.NĐ.CP.docx").

    Returns:
        Ordered list of ArticleBlock objects ready for chunk_builder.
    """
    parser = _LegalDocParser(doc_id, document_title, source_file)
    articles = parser.process(paragraphs)
    for w in parser.warnings:
        print(f"[WARN] {source_file}: {w}")
    return articles
