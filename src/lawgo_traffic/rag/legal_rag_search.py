from lawgo_traffic.rag.result_types import LegalRAGSearchResult


def legal_rag_search(
    query: str,
    intent: str | None = None,
    filters: dict | None = None,
    top_k: int = 5,
) -> LegalRAGSearchResult:
    """
    Core GraphRAG tool. Called by Main Agent when legal evidence is needed.
    Returns evidence + citations + graph_paths. Does NOT generate final answer.
    """
    # TODO: implement full retrieval pipeline:
    # 1. normalize query
    # 2. detect intent if not provided
    # 3. query LightRAG (hybrid mode)
    # 4. fallback to vector + BM25 if LightRAG result weak
    # 5. expand child → parent context
    # 6. build citations
    # 7. return LegalRAGSearchResult
    return LegalRAGSearchResult(query=query, intent=intent, status="not_implemented")
