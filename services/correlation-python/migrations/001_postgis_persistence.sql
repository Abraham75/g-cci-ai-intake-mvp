CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS normalized_events (
    id varchar(255) PRIMARY KEY,
    source_kind varchar(64) NOT NULL,
    source_system varchar(128) NOT NULL,
    source_record_id varchar(255) NOT NULL,
    source_url text,
    raw_sha256 varchar(64),
    correlation_processed_hash varchar(64),
    correlation_processed_at timestamptz,
    observed_at timestamptz NOT NULL,
    reported_at timestamptz,
    updated_at timestamptz,
    geom geography(Point,4326),
    roadway varchar(255),
    direction varchar(16),
    location_text text,
    event_type varchar(128) NOT NULL,
    description text NOT NULL DEFAULT '',
    lanes_affected varchar(255),
    commercial_vehicle_hint boolean NOT NULL DEFAULT false,
    injury_hint boolean NOT NULL DEFAULT false,
    fatality_hint boolean NOT NULL DEFAULT false,
    closure_hint boolean NOT NULL DEFAULT false,
    stalled_vehicle_hint boolean NOT NULL DEFAULT false,
    debris_hint boolean NOT NULL DEFAULT false,
    wheel_off_hint boolean NOT NULL DEFAULT false,
    attributes_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    raw_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    first_ingested_at timestamptz NOT NULL DEFAULT now(),
    last_ingested_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_event_source_record UNIQUE(source_system, source_record_id)
);

CREATE INDEX IF NOT EXISTS ix_event_geom ON normalized_events USING gist (geom);
CREATE INDEX IF NOT EXISTS ix_event_time_roadway ON normalized_events (observed_at, roadway);
CREATE INDEX IF NOT EXISTS ix_event_direction ON normalized_events (direction);
CREATE INDEX IF NOT EXISTS ix_event_processed_hash ON normalized_events (correlation_processed_hash);

CREATE TABLE IF NOT EXISTS incident_hypotheses (
    id varchar(64) PRIMARY KEY,
    current_revision integer NOT NULL DEFAULT 0,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    start_time timestamptz NOT NULL,
    end_time timestamptz NOT NULL,
    centroid geography(Point,4326),
    roadway varchar(255),
    direction varchar(16)
);

CREATE INDEX IF NOT EXISTS ix_hypothesis_centroid ON incident_hypotheses USING gist (centroid);
CREATE INDEX IF NOT EXISTS ix_hypothesis_time ON incident_hypotheses (start_time, end_time);
CREATE INDEX IF NOT EXISTS ix_hypothesis_roadway ON incident_hypotheses (roadway);

CREATE TABLE IF NOT EXISTS hypothesis_revisions (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    machine_confidence double precision NOT NULL,
    classification varchar(64) NOT NULL,
    status varchar(64) NOT NULL,
    model_version varchar(128) NOT NULL,
    rationale_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    contradictions_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    member_event_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    payload_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_hypothesis_revision UNIQUE(hypothesis_id, revision)
);

CREATE INDEX IF NOT EXISTS ix_hypothesis_revision_parent ON hypothesis_revisions(hypothesis_id, revision);

CREATE TABLE IF NOT EXISTS hypothesis_events (
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    event_id varchar(255) NOT NULL REFERENCES normalized_events(id) ON DELETE CASCADE,
    first_linked_revision integer NOT NULL,
    link_score double precision,
    linked_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(hypothesis_id, event_id)
);

CREATE INDEX IF NOT EXISTS ix_hypothesis_events_event ON hypothesis_events(event_id);

CREATE TABLE IF NOT EXISTS decision_ledger (
    sequence_no bigserial PRIMARY KEY,
    id varchar(64) UNIQUE NOT NULL,
    entry_type varchar(64) NOT NULL,
    subject_id varchar(128) NOT NULL,
    payload_json jsonb NOT NULL,
    produced_by varchar(255) NOT NULL,
    source_system varchar(255),
    model_version varchar(128),
    input_entry_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    supersedes_entry_id varchar(64),
    previous_hash varchar(64),
    entry_hash varchar(64) UNIQUE NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ledger_subject_sequence ON decision_ledger(subject_id, sequence_no);
CREATE INDEX IF NOT EXISTS ix_ledger_entry_type ON decision_ledger(entry_type);

-- Application roles should receive INSERT/SELECT only on decision_ledger.
-- Do not grant UPDATE or DELETE in production.
