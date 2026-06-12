from lawgo_traffic.agent.intent_router import detect_intent


class MainAgent:
    """ReAct agent stub. Wire LangGraph loop here."""

    def run(self, query: str, session_id: str | None = None) -> dict:
        intent = detect_intent(query)
        # TODO: implement LangGraph ReAct loop
        # 1. classify intent
        # 2. call legal_rag_search tool
        # 3. call additional tools (fine_calculator, rights_checker, ...)
        # 4. synthesize final answer with citations
        return {
            "answer": "[stub] Not implemented yet.",
            "intent": intent,
            "citations": [],
            "session_id": session_id,
        }
