CREATE TABLE IF NOT EXISTS score_jobs (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    score_input_json jsonb NOT NULL,
    materiality_json jsonb NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'PENDING',
    attempts integer NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_score_job_hypothesis_revision UNIQUE(hypothesis_id, revision)
);

CREATE INDEX IF NOT EXISTS ix_score_jobs_hypothesis ON score_jobs(hypothesis_id);
CREATE INDEX IF NOT EXISTS ix_score_jobs_status ON score_jobs(status);
CREATE INDEX IF NOT EXISTS ix_score_jobs_next_attempt ON score_jobs(next_attempt_at);
CREATE INDEX IF NOT EXISTS ix_score_jobs_ready ON score_jobs(status, next_attempt_at);

CREATE TABLE IF NOT EXISTS score_results (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    score double precision NOT NULL CHECK (score >= 0 AND score <= 1),
    tier varchar(1) NOT NULL CHECK (tier IN ('A','B','C','D')),
    model_version varchar(128) NOT NULL,
    result_json jsonb NOT NULL,
    scored_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_score_result_hypothesis_revision UNIQUE(hypothesis_id, revision)
);

CREATE INDEX IF NOT EXISTS ix_score_results_hypothesis ON score_results(hypothesis_id);
CREATE INDEX IF NOT EXISTS ix_score_results_tier ON score_results(tier);
CREATE INDEX IF NOT EXISTS ix_score_results_hypothesis_scored ON score_results(hypothesis_id, scored_at);
