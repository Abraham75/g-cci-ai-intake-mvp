from app.ledger import append_entry, list_entries


class AuditRepository:
    def append(self, entity_type: str, entity_id: str, action: str, payload: dict, actor: str):
        return append_entry(
            aggregate_type=entity_type,
            aggregate_id=entity_id,
            event_type=action,
            payload=payload,
            actor=actor,
        )

    def list(self) -> list[dict]:
        return [entry.model_dump() for entry in list_entries()]
