CREATE TABLE IF NOT EXISTS validation_benchmark_matches (
    id varchar(64) PRIMARY KEY,
    benchmark_id varchar(64) NOT NULL
        REFERENCES validation_benchmark_cases(id) ON DELETE CASCADE,
    hypothesis_id varchar(64) NOT NULL
        REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    match_evidence text NOT NULL,
    matched_by varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_validation_benchmark_match_history
    ON validation_benchmark_matches(benchmark_id, created_at DESC);
