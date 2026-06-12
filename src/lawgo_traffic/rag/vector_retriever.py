class VectorRetriever:
    """Qdrant Cloud vector search stub."""

    def __init__(self, url: str, api_key: str, collection: str = "lawgo_chunks"):
        # TODO: init qdrant client
        pass

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        # TODO: embed query and search Qdrant
        raise NotImplementedError

    def upsert(self, chunks: list[dict]) -> None:
        # TODO: embed and upsert chunks
        raise NotImplementedError
