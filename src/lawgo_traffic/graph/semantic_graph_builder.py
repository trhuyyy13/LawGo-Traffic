def build_semantic_graph(children: list[dict]) -> list[dict]:
    """
    Extract semantic entities/relations from child chunks using LightRAG/LLM.
    Returns list of edge dicts with richer relations (REGULATES, HAS_PENALTY, ...).
    """
    # TODO: implement via LightRAG entity extraction
    raise NotImplementedError
