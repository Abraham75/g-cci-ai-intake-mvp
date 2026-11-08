ALTER TABLE hypothesis_events
    ADD COLUMN IF NOT EXISTS last_evaluated_revision integer,
    ADD COLUMN IF NOT EXISTS active boolean NOT NULL DEFAULT true;

UPDATE hypothesis_events
SET last_evaluated_revision = first_linked_revision
WHERE last_evaluated_revision IS NULL;

ALTER TABLE hypothesis_events
    ALTER COLUMN last_evaluated_revision SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_hypothesis_events_active
    ON hypothesis_events(hypothesis_id, active);
