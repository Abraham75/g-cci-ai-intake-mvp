from dataclasses import dataclass, field
from typing import Dict, List, Any
import time

@dataclass
class InMemoryStore:
    leads: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    lead_order: List[str] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)

    def add_lead(self, lead_id: str, payload: Dict[str, Any]):
        self.leads[lead_id] = payload
        self.lead_order.insert(0, lead_id)

    def latest_leads(self, limit: int = 5):
        return [self.leads[i] for i in self.lead_order[:limit]]

    def add_alert(self, alert: Dict[str, Any]):
        alert["ts"] = int(time.time() * 1000)
        self.alerts.insert(0, alert)
        self.alerts = self.alerts[:5]

STORE = InMemoryStore()
