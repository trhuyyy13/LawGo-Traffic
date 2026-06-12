INTENT_FINE_LOOKUP = "fine_lookup"
INTENT_MULTI_VIOLATION = "multi_violation"
INTENT_RIGHTS_LOOKUP = "rights_lookup"
INTENT_AUTHORITY_LOOKUP = "authority_lookup"
INTENT_PROCEDURE_LOOKUP = "procedure_lookup"
INTENT_LEGAL_EXPLAIN = "legal_explain"
INTENT_OUT_OF_SCOPE = "out_of_scope"
INTENT_UNKNOWN = "unknown"


def detect_intent(query: str) -> str:
    """Keyword-based intent router. Replace with LLM classifier later."""
    # TODO: implement
    return INTENT_UNKNOWN
