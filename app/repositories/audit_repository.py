from app.ledger import append_entry, get_entries


class AuditRepository:
    def append(self, entity_type: str, entity_id: str, action: str, payload: dict, actor: str) -> dict:
        return append_entry(entity_type=entity_type, entity_id=entity_id, action=action, payload=payload, actor=actor)

    def list(self) -> list[dict]:
        return get_entries()
