from fastapi import APIRouter, HTTPException

from lawgo_traffic.api.schemas import ChatRequest, ChatResponse, LegalRAGSearchRequest, LegalRAGSearchResponse

router = APIRouter(prefix="/chat", tags=["chat"])
rag_router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if request.audio and request.message:
        raise HTTPException(status_code=400, detail="Provide either message or audio, not both.")
    # TODO: wire to main_agent
    return ChatResponse(answer="[stub] Not implemented yet.", session_id=request.session_id)


@rag_router.post("/legal-rag-search", response_model=LegalRAGSearchResponse)
async def legal_rag_search(request: LegalRAGSearchRequest) -> LegalRAGSearchResponse:
    # TODO: wire to rag.legal_rag_search
    return LegalRAGSearchResponse(
        query=request.query,
        intent=request.intent,
        status="ok",
    )
