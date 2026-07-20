class RagAdapter:
    """Retrieval boundary for Georgia tort, FMCSA, trucking case law, and firm corpora."""

    def __init__(self, retriever=None):
        self.retriever = retriever

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        if self.retriever is None:
            return []
        return list(self.retriever.retrieve(query=query, top_k=top_k))
