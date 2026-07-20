class AlertService:
    def prioritize(self, alerts: list[dict[str, str]]) -> list[dict[str, str]]:
        priority = {"CRITICAL": 0, "WARN": 1, "INFO": 2}
        return sorted(alerts, key=lambda item: priority.get(item.get("level", "INFO"), 99))
