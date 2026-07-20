from app.domain.intake_scoring import DecisionEngine


class DecisionService:
    def __init__(self):
        self.engine = DecisionEngine()

    def score(self, lead: dict) -> dict:
        return self.engine.score(lead)
