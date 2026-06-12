def build_structural_graph(parents: list[dict], children: list[dict]) -> list[dict]:
    """
    Build deterministic Document → Article → Clause → Point edges from chunks.
    Rule-based only — no LLM.
    Returns list of edge dicts: {source, relation, target}.
    """
    # TODO: implement
    raise NotImplementedError
