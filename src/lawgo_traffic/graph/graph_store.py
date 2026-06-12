class GraphStore:
    """Neo4j AuraDB adapter stub."""

    def __init__(self, uri: str, user: str, password: str):
        # TODO: init neo4j driver
        pass

    def upsert_nodes(self, nodes: list[dict]) -> None:
        # TODO: implement
        raise NotImplementedError

    def upsert_edges(self, edges: list[dict]) -> None:
        # TODO: implement
        raise NotImplementedError

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        # TODO: implement
        raise NotImplementedError

    def close(self) -> None:
        pass
