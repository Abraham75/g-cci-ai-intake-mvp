class ShapAdapter:
    """Optional explainability adapter; deterministic explanations remain the MVP fallback."""

    def __init__(self, explainer=None):
        self.explainer = explainer

    def explain(self, feature_vector):
        if self.explainer is None:
            return None
        return self.explainer(feature_vector)
