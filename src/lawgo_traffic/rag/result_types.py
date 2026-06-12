from dataclasses import dataclass, field


@dataclass
class AnswerBasis:
    content: str = ""
    parent_context: str = ""
    document: str = ""
    article: str = ""
    clause: str = ""
    point: str = ""
    source_chunk_id: str = ""
    parent_id: str = ""
    score: float = 0.0


@dataclass
class LegalRAGSearchResult:
    query: str = ""
    intent: str | None = None
    answer_basis: list[AnswerBasis] = field(default_factory=list)
    graph_paths: list[dict] = field(default_factory=list)
    matched_entities: list[dict] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "ok"
    warnings: list[str] = field(default_factory=list)
