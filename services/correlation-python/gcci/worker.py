from __future__ import annotations

import asyncio
import logging

from sqlalchemy import or_, select

from .config import settings
from .database import EventRow, SessionLocal
from .persistence_service import PersistentCorrelationService
from .repository import event_row_to_model


log = logging.getLogger("gcci.correlation.worker")
service = PersistentCorrelationService()


async def fetch_pending_events(limit: int) -> list[EventRow]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(EventRow)
                .where(
                    or_(
                        EventRow.correlation_processed_hash.is_(None),
                        EventRow.correlation_processed_hash != EventRow.raw_sha256,
                    )
                )
                .order_by(EventRow.last_ingested_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)


async def process_event(event_row: EventRow) -> None:
    event = event_row_to_model(event_row)
    async with SessionLocal() as session:
        try:
            async with session.begin():
                hypothesis_ids = await service.correlate_event(session, event)
            log.info("processed event=%s hypotheses=%s", event.id, hypothesis_ids)
        except Exception:
            log.exception("correlation failed event=%s", event.id)
            raise


async def run_forever() -> None:
    logging.basicConfig(level=logging.INFO)
    log.info("starting G-CCI correlation worker")

    while True:
        rows = await fetch_pending_events(settings.worker_batch_size)
        if not rows:
            await asyncio.sleep(settings.worker_poll_seconds)
            continue

        for row in rows:
            try:
                await process_event(row)
            except Exception:
                # Failed records remain unprocessed and will be retried on the next poll.
                await asyncio.sleep(0.25)


if __name__ == "__main__":
    asyncio.run(run_forever())
