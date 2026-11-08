CREATE TABLE IF NOT EXISTS orchestration_runs (
    id varchar(64) PRIMARY KEY,
    objective text NOT NULL,
    audience text NOT NULL,
    deliverable text NOT NULL,
    constraints_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    success_criteria_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    status varchar(32) NOT NULL DEFAULT 'PLANNING'
        CHECK (status IN ('PLANNING','RUNNING','REVIEW','BLOCKED','SUCCEEDED','FAILED')),
    requested_by varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orchestration_tasks (
    id varchar(64) PRIMARY KEY,
    run_id varchar(64) NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    role varchar(64) NOT NULL,
    objective text NOT NULL,
    brief_json jsonb NOT NULL,
    depends_on_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    state varchar(32) NOT NULL DEFAULT 'PENDING'
        CHECK (state IN ('PENDING','READY','RUNNING','BLOCKED','REVIEW_REQUIRED','SUCCEEDED','FAILED')),
    requires_human_approval boolean NOT NULL DEFAULT false,
    approved_by varchar(255),
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(run_id, id)
);
CREATE INDEX IF NOT EXISTS ix_orchestration_tasks_run_state
    ON orchestration_tasks(run_id, state);

CREATE TABLE IF NOT EXISTS agent_handoffs (
    id varchar(64) PRIMARY KEY,
    run_id varchar(64) NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    task_id varchar(64) NOT NULL REFERENCES orchestration_tasks(id) ON DELETE CASCADE,
    role varchar(64) NOT NULL,
    handoff_json jsonb NOT NULL,
    confidence double precision NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_agent_handoffs_task ON agent_handoffs(task_id, created_at DESC);

CREATE TABLE IF NOT EXISTS evidence_claims (
    id varchar(64) PRIMARY KEY,
    run_id varchar(64) NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    task_id varchar(64) REFERENCES orchestration_tasks(id) ON DELETE SET NULL,
    statement text NOT NULL,
    epistemic_status varchar(16) NOT NULL
        CHECK (epistemic_status IN ('Verified','Inferred','Assumed','Opinion')),
    evidence_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (epistemic_status <> 'Verified' OR jsonb_array_length(evidence_ids_json) > 0)
);

CREATE TABLE IF NOT EXISTS orchestration_review_findings (
    id varchar(64) PRIMARY KEY,
    run_id varchar(64) NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    task_id varchar(64) REFERENCES orchestration_tasks(id) ON DELETE SET NULL,
    severity varchar(16) NOT NULL CHECK (severity IN ('Critical','Major','Minor')),
    issue text NOT NULL,
    proposed_fix text NOT NULL,
    evidence_ids_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    resolved boolean NOT NULL DEFAULT false,
    resolved_by varchar(255),
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_orchestration_findings_release
    ON orchestration_review_findings(run_id, severity, resolved);

CREATE TABLE IF NOT EXISTS orchestration_change_log (
    id varchar(64) PRIMARY KEY,
    run_id varchar(64) NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    finding_id varchar(64) REFERENCES orchestration_review_findings(id) ON DELETE SET NULL,
    responsible_role varchar(64) NOT NULL,
    correction text NOT NULL,
    remains_unresolved boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orchestration_release_decisions (
    id varchar(64) PRIMARY KEY,
    run_id varchar(64) NOT NULL REFERENCES orchestration_runs(id) ON DELETE CASCADE,
    releasable boolean NOT NULL,
    decision_json jsonb NOT NULL,
    decided_by varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
