class MapboxAdapter:
    """Optional geospatial rendering/enrichment boundary for the dashboard."""

    def __init__(self, token: str | None = None):
        self.token = token

    def enabled(self) -> bool:
        return bool(self.token)
