CREATE TABLE IF NOT EXISTS validation_benchmark_cases (
    id varchar(64) PRIMARY KEY,
    external_reference varchar(255) NOT NULL UNIQUE,
    source varchar(255) NOT NULL,
    occurred_at timestamptz NOT NULL,
    roadway varchar(255),
    known_valuable boolean NOT NULL,
    traditional_awareness_at timestamptz,
    matched_hypothesis_id varchar(64) REFERENCES incident_hypotheses(id) ON DELETE SET NULL,
    match_evidence text,
    note text,
    created_by varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    matched_at timestamptz
);
CREATE INDEX IF NOT EXISTS ix_validation_benchmark_valuable
    ON validation_benchmark_cases(known_valuable);
CREATE INDEX IF NOT EXISTS ix_validation_benchmark_match
    ON validation_benchmark_cases(matched_hypothesis_id);
