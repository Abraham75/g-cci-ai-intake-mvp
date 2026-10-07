CREATE TABLE IF NOT EXISTS evidence_acquisition_tasks (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    score_result_id varchar(64) NOT NULL REFERENCES score_results(id) ON DELETE CASCADE,
    evidence_type varchar(64) NOT NULL,
    question text NOT NULL,
    recommended_action text NOT NULL,
    expected_information_gain double precision NOT NULL CHECK (expected_information_gain >= 0 AND expected_information_gain <= 1),
    acquisition_priority_score double precision NOT NULL CHECK (acquisition_priority_score >= 0 AND acquisition_priority_score <= 1),
    case_opportunity_score double precision NOT NULL CHECK (case_opportunity_score >= 0 AND case_opportunity_score <= 1),
    tier varchar(1) NOT NULL CHECK (tier IN ('A','B','C','D')),
    status varchar(32) NOT NULL DEFAULT 'OPEN',
    priority_model_version varchar(128) NOT NULL,
    gap_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_acquisition_task_revision_type UNIQUE(hypothesis_id, revision, evidence_type)
);

CREATE INDEX IF NOT EXISTS ix_acquisition_tasks_hypothesis ON evidence_acquisition_tasks(hypothesis_id);
CREATE INDEX IF NOT EXISTS ix_acquisition_tasks_status ON evidence_acquisition_tasks(status);
CREATE INDEX IF NOT EXISTS ix_acquisition_tasks_priority ON evidence_acquisition_tasks(acquisition_priority_score DESC);
CREATE INDEX IF NOT EXISTS ix_acquisition_tasks_open_priority ON evidence_acquisition_tasks(status, acquisition_priority_score DESC);
