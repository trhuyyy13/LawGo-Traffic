from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str | None = None
    audio: str | None = None  # base64-encoded audio; mutually exclusive with message
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict] = []
    session_id: str | None = None


class LegalRAGSearchRequest(BaseModel):
    query: str
    intent: str | None = None
    filters: dict | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class AnswerBasis(BaseModel):
    content: str = ""
    parent_context: str = ""
    document: str = ""
    article: str = ""
    clause: str = ""
    point: str = ""
    source_chunk_id: str = ""
    parent_id: str = ""
    score: float = 0.0


class GraphPath(BaseModel):
    path: list[str] = []
    source_chunk_id: str = ""


class MatchedEntity(BaseModel):
    name: str = ""
    type: str = ""
    confidence: float = 0.0


class Citation(BaseModel):
    document: str = ""
    article: str = ""
    clause: str = ""
    point: str = ""
    source_chunk_id: str = ""


class LegalRAGSearchResponse(BaseModel):
    query: str
    intent: str | None = None
    answer_basis: list[AnswerBasis] = []
    graph_paths: list[GraphPath] = []
    matched_entities: list[MatchedEntity] = []
    citations: list[Citation] = []
    confidence: float = 0.0
    status: str = "ok"
    warnings: list[str] = []
