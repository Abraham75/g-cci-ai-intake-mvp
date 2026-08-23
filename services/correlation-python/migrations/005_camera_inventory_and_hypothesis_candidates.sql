CREATE TABLE IF NOT EXISTS traffic_cameras (
    id varchar(128) PRIMARY KEY,
    source_system varchar(128) NOT NULL DEFAULT 'GDOT_CAMERA',
    source_record_id varchar(255) NOT NULL,
    name varchar(255) NOT NULL,
    roadway varchar(255),
    direction varchar(16),
    latitude double precision NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude double precision NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    geom geography(POINT, 4326) NOT NULL,
    snapshot_url text,
    stream_url text,
    active boolean NOT NULL DEFAULT true,
    raw_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_camera_source_record UNIQUE(source_system, source_record_id)
);

CREATE INDEX IF NOT EXISTS ix_traffic_cameras_geom
    ON traffic_cameras USING gist (geom);
CREATE INDEX IF NOT EXISTS ix_traffic_cameras_roadway_direction
    ON traffic_cameras(roadway, direction);
CREATE INDEX IF NOT EXISTS ix_traffic_cameras_active
    ON traffic_cameras(active);

CREATE TABLE IF NOT EXISTS hypothesis_camera_candidates (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    camera_id varchar(128) NOT NULL REFERENCES traffic_cameras(id) ON DELETE CASCADE,
    distance_meters double precision NOT NULL CHECK (distance_meters >= 0),
    roadway_match boolean NOT NULL DEFAULT false,
    direction_match boolean NOT NULL DEFAULT false,
    relevance_score double precision NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 1),
    preservation_window_start timestamptz NOT NULL,
    preservation_window_end timestamptz NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'CURRENT',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_hypothesis_camera_revision UNIQUE(hypothesis_id, revision, camera_id)
);

CREATE INDEX IF NOT EXISTS ix_hypothesis_camera_hypothesis_revision
    ON hypothesis_camera_candidates(hypothesis_id, revision);
CREATE INDEX IF NOT EXISTS ix_hypothesis_camera_relevance
    ON hypothesis_camera_candidates(hypothesis_id, revision, relevance_score DESC);
CREATE INDEX IF NOT EXISTS ix_hypothesis_camera_status
    ON hypothesis_camera_candidates(status);
