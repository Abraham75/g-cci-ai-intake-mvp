class XGBoostAdapter:
    """Replaceable model adapter. MVP falls back to deterministic domain scoring."""

    def __init__(self, model=None):
        self.model = model

    def predict_proba(self, features: dict[str, float]) -> float | None:
        if self.model is None:
            return None
        vector = [[features[key] for key in sorted(features)]]
        return float(self.model.predict_proba(vector)[0][1])
