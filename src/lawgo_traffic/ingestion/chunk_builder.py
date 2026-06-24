from lawgo_traffic.ingestion.id_utils import make_article_id, make_clause_id, make_point_id
from lawgo_traffic.ingestion.legal_parser import ArticleBlock


def _article_label(number: str) -> str:
    return f"Điều {number}"


def _clause_label(number: str) -> str:
    return f"Khoản {number}"


def _point_label(letter: str) -> str:
    return f"Điểm {letter}"


def _build_parent_text(article: ArticleBlock) -> str:
    """Reconstruct article text preserving logical structure."""
    parts: list[str] = [f"{_article_label(article.article_number)}. {article.article_title}"]
    for clause in article.clauses:
        parts.append(f"{clause.number}. {clause.clause_header}")
        for point in clause.points:
            parts.append(f"{point.letter}) {point.text_raw}")
    if article.body_text:
        parts.append(article.body_text)
    return "\n".join(parts)


def build_all_chunks(
    articles: list[ArticleBlock],
) -> tuple[list[dict], list[dict]]:
    """Build parent and child chunks from parsed ArticleBlock list.

    Parent chunks = one per Article (ARTICLE type).
    Child chunks  = per Point (POINT), per clause-without-points (CLAUSE),
                    or one per article-without-clauses (ARTICLE_CHILD).

    Returns:
        (parents, children) — both are lists of dicts ready for JSONL serialisation.
    """
    parents: list[dict] = []
    children: list[dict] = []
    seen_chunk_ids: dict[str, int] = {}   # base_id → occurrence count
    warnings: list[str] = []

    for article in articles:
        parent_id = make_article_id(article.doc_id, article.article_number)
        art_label = _article_label(article.article_number)

        # --- parent chunk ---
        parent: dict = {
            "parent_id": parent_id,
            "doc_id": article.doc_id,
            "chunk_type": "ARTICLE",
            "document_title": article.document_title,
            "chapter": article.chapter,
            "chapter_title": article.chapter_title,
            "section": article.section,
            "section_title": article.section_title,
            "article": art_label,
            "article_title": article.article_title,
            "text": _build_parent_text(article),
            "source_file": article.source_file,
        }
        parents.append(parent)

        # --- child chunks ---
        if not article.clauses:
            # Case C — ARTICLE_CHILD (article with no clauses)
            if article.clauses:
                # Sanity: should never hit this branch if clauses exist.
                warnings.append(f"W07: ARTICLE_CHILD logic conflict for {parent_id}")

            chunk_id = _unique_chunk_id(parent_id, seen_chunk_ids, warnings)

            text_for_search = (
                f"{article.document_title}. "
                f"{art_label}. {article.article_title}. "
                f"{article.body_text}"
            )

            children.append({
                "chunk_id": chunk_id,
                "parent_id": parent_id,
                "doc_id": article.doc_id,
                "chunk_type": "ARTICLE_CHILD",
                "text_raw": article.body_text,
                "clause_header": None,
                "text_for_search": text_for_search.strip(),
                "legal_path": {
                    "document_title": article.document_title,
                    "chapter": article.chapter,
                    "chapter_title": article.chapter_title,
                    "section": article.section,
                    "section_title": article.section_title,
                    "article": art_label,
                    "article_title": article.article_title,
                    "clause": None,
                    "clause_header": None,
                    "point": None,
                },
                "source_file": article.source_file,
            })

        else:
            for clause in article.clauses:
                cl_label = _clause_label(clause.number)

                if clause.points:
                    # Case A — POINT children
                    for point in clause.points:
                        pt_label = _point_label(point.letter)
                        base_id = make_point_id(
                            article.doc_id,
                            article.article_number,
                            clause.number,
                            point.letter,
                        )
                        chunk_id = _unique_chunk_id(base_id, seen_chunk_ids, warnings)
                        _check_short_text(chunk_id, point.text_raw, warnings)

                        text_for_search = (
                            f"{article.document_title}. "
                            f"{art_label}. {article.article_title}. "
                            f"{cl_label}. {clause.clause_header}. "
                            f"{pt_label}. {point.text_raw}"
                        )

                        children.append({
                            "chunk_id": chunk_id,
                            "parent_id": parent_id,
                            "doc_id": article.doc_id,
                            "chunk_type": "POINT",
                            "text_raw": point.text_raw,
                            "clause_header": clause.clause_header,
                            "text_for_search": text_for_search,
                            "legal_path": {
                                "document_title": article.document_title,
                                "chapter": article.chapter,
                                "chapter_title": article.chapter_title,
                                "section": article.section,
                                "section_title": article.section_title,
                                "article": art_label,
                                "article_title": article.article_title,
                                "clause": cl_label,
                                "clause_header": clause.clause_header,
                                "point": pt_label,
                            },
                            "source_file": article.source_file,
                        })

                else:
                    # Case B — CLAUSE child (clause with no points)
                    base_id = make_clause_id(
                        article.doc_id,
                        article.article_number,
                        clause.number,
                    )
                    chunk_id = _unique_chunk_id(base_id, seen_chunk_ids, warnings)
                    _check_short_text(chunk_id, clause.clause_header, warnings)

                    text_for_search = (
                        f"{article.document_title}. "
                        f"{art_label}. {article.article_title}. "
                        f"{cl_label}. {clause.clause_header}"
                    )

                    children.append({
                        "chunk_id": chunk_id,
                        "parent_id": parent_id,
                        "doc_id": article.doc_id,
                        "chunk_type": "CLAUSE",
                        "text_raw": clause.clause_header,
                        "clause_header": None,
                        "text_for_search": text_for_search,
                        "legal_path": {
                            "document_title": article.document_title,
                            "chapter": article.chapter,
                            "chapter_title": article.chapter_title,
                            "section": article.section,
                            "section_title": article.section_title,
                            "article": art_label,
                            "article_title": article.article_title,
                            "clause": cl_label,
                            "clause_header": None,
                            "point": None,
                        },
                        "source_file": article.source_file,
                    })

    for w in warnings:
        print(f"[WARN] chunk_builder: {w}")

    return parents, children


def build_validation_report(
    source_file: str,
    doc_id: str,
    articles: list[ArticleBlock],
    parents: list[dict],
    children: list[dict],
) -> dict:
    """Build a validation report and surface any warning-level issues."""
    total_clauses = sum(len(a.clauses) for a in articles)
    total_points = sum(
        len(cl.points) for a in articles for cl in a.clauses
    )

    by_type: dict[str, int] = {}
    for ch in children:
        ct = ch["chunk_type"]
        by_type[ct] = by_type.get(ct, 0) + 1

    warnings: list[str] = []

    # W05 — post-hoc duplicate check (build_all_chunks already disambiguates;
    # this catches any remaining true duplicates after suffix assignment)
    seen: set[str] = set()
    for ch in children:
        cid = ch["chunk_id"]
        if cid in seen:
            warnings.append(f"W05: still-duplicate chunk_id '{cid}' after suffix assignment")
        seen.add(cid)

    # W06 — POINT chunk missing clause_header
    for ch in children:
        if ch["chunk_type"] == "POINT" and not ch.get("clause_header"):
            warnings.append(f"W06: POINT chunk missing clause_header: {ch['chunk_id']}")

    # W07 — ARTICLE_CHILD but article has clauses
    for ch in children:
        if ch["chunk_type"] == "ARTICLE_CHILD":
            pid = ch["parent_id"]
            art = next((a for a in articles if make_article_id(a.doc_id, a.article_number) == pid), None)
            if art and art.clauses:
                warnings.append(f"W07: ARTICLE_CHILD but Điều has clauses: {pid}")

    # W04 — short text_raw
    for ch in children:
        if len(ch.get("text_raw", "")) < 10:
            warnings.append(f"W04: short text_raw in {ch['chunk_id']}")

    # W08 — low-confidence OCR marker present in chunk text
    for ch in children:
        if "[KHÔNG RÕ:" in ch.get("text_raw", ""):
            warnings.append(f"W08: low-confidence OCR text in {ch['chunk_id']}")

    report = {
        "source_file": source_file,
        "doc_id": doc_id,
        "total_articles": len(articles),
        "total_clauses": total_clauses,
        "total_points": total_points,
        "parents_count": len(parents),
        "children_count": len(children),
        "children_by_type": by_type,
        "warnings": warnings,
    }

    # Print summary
    print(
        f"[REPORT] {source_file}: "
        f"{len(articles)} articles / {total_clauses} clauses / {total_points} points "
        f"→ {len(children)} children {by_type}"
    )
    for w in warnings:
        print(f"  [WARN] {w}")

    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_chunk_id(base_id: str, seen: dict[str, int], warnings: list[str]) -> str:
    """Return a unique chunk_id, appending _2/_3/... if the base is taken.

    Real documents (e.g. NĐ168 Điều 40 Khoản 3) occasionally have duplicate
    point labels — this is an error in the source Word file, not a parser bug.
    We log W05 and produce a stable, unique ID rather than silently overwriting.
    """
    if base_id not in seen:
        seen[base_id] = 1
        return base_id
    seen[base_id] += 1
    suffix_id = f"{base_id}_{seen[base_id]}"
    warnings.append(
        f"W05: duplicate point label → source document error; "
        f"'{base_id}' already exists, assigned '{suffix_id}'"
    )
    return suffix_id


def _check_short_text(chunk_id: str, text: str, warnings: list[str]) -> None:
    if len(text.strip()) < 10:
        warnings.append(f"W04: short text_raw in '{chunk_id}': '{text[:30]}'")
