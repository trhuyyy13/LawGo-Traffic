class LightRAGAdapter:
    """Wraps LightRAG so the rest of the app has no direct LightRAG dependency."""

    def __init__(self, working_dir: str):
        self.working_dir = working_dir
        # TODO: init LightRAG instance

    def index_chunks(self, chunks: list[dict]) -> None:
        # TODO: insert text_for_search from each chunk into LightRAG
        raise NotImplementedError

    def query(self, query: str, mode: str = "hybrid") -> dict:
        # TODO: call LightRAG query and return raw result
        raise NotImplementedError
