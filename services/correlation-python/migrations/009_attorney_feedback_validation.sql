CREATE TABLE IF NOT EXISTS attorney_case_reviews (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    score_revision integer,
    disposition varchar(40) NOT NULL CHECK (disposition IN (
        'GOOD_CASE','BAD_CASE','NEEDS_MORE_INFORMATION','DUPLICATE',
        'NOT_A_TRUCK_CASE','INSUFFICIENT_INJURY','LIABILITY_TOO_WEAK',
        'NO_COLLECTIBLE_DEFENDANT','ALREADY_REPRESENTED','OTHER'
    )),
    attorney_worthy boolean,
    reason_code varchar(80),
    note text,
    reviewed_by varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_attorney_reviews_hypothesis_created
    ON attorney_case_reviews(hypothesis_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_attorney_reviews_worthy
    ON attorney_case_reviews(attorney_worthy) WHERE attorney_worthy IS NOT NULL;

CREATE TABLE IF NOT EXISTS case_outcomes (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    stage varchar(32) NOT NULL CHECK (stage IN (
        'INVESTIGATED','ADVANCED','SIGNED','DECLINED','REFERRED','LOST','SETTLED'
    )),
    traditional_awareness_at timestamptz,
    note text,
    recorded_by varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_case_outcomes_hypothesis_created
    ON case_outcomes(hypothesis_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_case_outcomes_stage ON case_outcomes(stage);
