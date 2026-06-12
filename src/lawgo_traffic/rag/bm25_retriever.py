class BM25Retriever:
    """BM25 keyword search stub."""

    def __init__(self):
        self._index = None

    def build_index(self, chunks: list[dict]) -> None:
        # TODO: build bm25s index from text_for_search
        raise NotImplementedError

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        # TODO: search index and return ranked chunks
        raise NotImplementedError
