CREATE TABLE IF NOT EXISTS prospect_resolution_records (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    party_role varchar(64) NOT NULL DEFAULT 'INJURED_PARTY',
    stage varchar(32) NOT NULL DEFAULT 'UNKNOWN'
        CHECK (stage IN ('UNKNOWN','CANDIDATE','CORROBORATED','VERIFIED')),
    display_label varchar(255),
    source_type varchar(64),
    source_reference varchar(255),
    confidence double precision NOT NULL DEFAULT 0
        CHECK (confidence >= 0 AND confidence <= 1),
    verified boolean NOT NULL DEFAULT false,
    lawful_access_basis varchar(64) NOT NULL DEFAULT 'NotEstablished',
    notes_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_prospect_resolution_hypothesis
    ON prospect_resolution_records(hypothesis_id);
CREATE INDEX IF NOT EXISTS ix_prospect_resolution_stage
    ON prospect_resolution_records(stage);

CREATE TABLE IF NOT EXISTS resolution_tasks (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    task_type varchar(64) NOT NULL,
    source_type varchar(64) NOT NULL,
    question text NOT NULL,
    recommended_action text NOT NULL,
    probability_exists double precision NOT NULL CHECK (probability_exists >= 0 AND probability_exists <= 1),
    probability_resolves double precision NOT NULL CHECK (probability_resolves >= 0 AND probability_resolves <= 1),
    source_reliability double precision NOT NULL CHECK (source_reliability >= 0 AND source_reliability <= 1),
    lawful_access_factor double precision NOT NULL CHECK (lawful_access_factor >= 0 AND lawful_access_factor <= 1),
    urgency double precision NOT NULL CHECK (urgency >= 0 AND urgency <= 1),
    resolution_priority_score double precision NOT NULL CHECK (resolution_priority_score >= 0 AND resolution_priority_score <= 1),
    status varchar(32) NOT NULL DEFAULT 'OPEN',
    model_version varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_resolution_task_revision_source UNIQUE(hypothesis_id, revision, task_type, source_type)
);

CREATE INDEX IF NOT EXISTS ix_resolution_tasks_hypothesis_revision
    ON resolution_tasks(hypothesis_id, revision);
CREATE INDEX IF NOT EXISTS ix_resolution_tasks_open_priority
    ON resolution_tasks(status, resolution_priority_score DESC);

CREATE TABLE IF NOT EXISTS lead_qualification_snapshots (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    score_result_id varchar(64) NOT NULL REFERENCES score_results(id) ON DELETE CASCADE,
    stage varchar(32) NOT NULL
        CHECK (stage IN ('S0_SIGNAL','S1_OPPORTUNITY','S2_QUALIFIED_CASE','S3_RESOLVED_PROSPECT')),
    qualification_score double precision NOT NULL CHECK (qualification_score >= 0 AND qualification_score <= 1),
    case_qualified boolean NOT NULL DEFAULT false,
    claimant_resolution_stage varchar(32) NOT NULL DEFAULT 'UNKNOWN'
        CHECK (claimant_resolution_stage IN ('UNKNOWN','CANDIDATE','CORROBORATED','VERIFIED')),
    claimant_resolution_score double precision NOT NULL DEFAULT 0
        CHECK (claimant_resolution_score >= 0 AND claimant_resolution_score <= 1),
    contact_eligibility varchar(32) NOT NULL DEFAULT 'NOT_EVALUATED',
    dimensions_json jsonb NOT NULL,
    reasons_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    blockers_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    required_actions_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    model_version varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_lead_qualification_revision UNIQUE(hypothesis_id, revision)
);

CREATE INDEX IF NOT EXISTS ix_lead_qualification_hypothesis_revision
    ON lead_qualification_snapshots(hypothesis_id, revision DESC);
CREATE INDEX IF NOT EXISTS ix_lead_qualification_stage
    ON lead_qualification_snapshots(stage);
CREATE INDEX IF NOT EXISTS ix_lead_qualification_score
    ON lead_qualification_snapshots(qualification_score DESC);
