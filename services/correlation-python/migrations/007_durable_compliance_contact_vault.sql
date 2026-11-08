CREATE TABLE IF NOT EXISTS compliance_gate_states (
    hypothesis_id varchar(64) PRIMARY KEY REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    legal_access_basis varchar(64) NOT NULL DEFAULT 'NotEstablished',
    solicitation_review_status varchar(64) NOT NULL DEFAULT 'NotReviewed',
    solicitation_hold_days integer,
    suppression_checked boolean NOT NULL DEFAULT false,
    contact_eligibility_status varchar(32) NOT NULL DEFAULT 'NotEvaluated'
        CHECK (contact_eligibility_status IN ('NotEvaluated','Ineligible','Eligible')),
    notes_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    reviewed_by varchar(255),
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_compliance_gate_eligibility
    ON compliance_gate_states(contact_eligibility_status);

CREATE TABLE IF NOT EXISTS contact_points (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    prospect_id varchar(64) NOT NULL REFERENCES prospect_resolution_records(id) ON DELETE CASCADE,
    contact_type varchar(32) NOT NULL CHECK (contact_type IN ('PHONE','EMAIL','ADDRESS','OTHER')),
    encrypted_value bytea NOT NULL,
    nonce bytea NOT NULL,
    value_fingerprint varchar(64) NOT NULL,
    masked_value varchar(255) NOT NULL,
    source_type varchar(64) NOT NULL,
    source_reference varchar(255) NOT NULL,
    lawful_access_basis varchar(64) NOT NULL,
    verification_confidence double precision NOT NULL DEFAULT 0
        CHECK (verification_confidence >= 0 AND verification_confidence <= 1),
    verified boolean NOT NULL DEFAULT false,
    status varchar(32) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SUPPRESSED','REVOKED')),
    created_by varchar(255) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_contact_fingerprint_hypothesis UNIQUE(hypothesis_id, value_fingerprint)
);

CREATE INDEX IF NOT EXISTS ix_contact_points_hypothesis
    ON contact_points(hypothesis_id);
CREATE INDEX IF NOT EXISTS ix_contact_points_prospect
    ON contact_points(prospect_id);
CREATE INDEX IF NOT EXISTS ix_contact_points_status
    ON contact_points(status);

CREATE TABLE IF NOT EXISTS contact_access_audit (
    id varchar(64) PRIMARY KEY,
    contact_point_id varchar(64) NOT NULL REFERENCES contact_points(id) ON DELETE CASCADE,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    actor varchar(255) NOT NULL,
    action varchar(64) NOT NULL,
    reason text NOT NULL,
    allowed boolean NOT NULL,
    gate_snapshot_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_contact_access_audit_contact
    ON contact_access_audit(contact_point_id, created_at DESC);

CREATE TABLE IF NOT EXISTS outreach_activation_attempts (
    id varchar(64) PRIMARY KEY,
    hypothesis_id varchar(64) NOT NULL REFERENCES incident_hypotheses(id) ON DELETE CASCADE,
    requested_by varchar(255) NOT NULL,
    allowed boolean NOT NULL,
    reason text,
    gate_snapshot_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_outreach_activation_hypothesis
    ON outreach_activation_attempts(hypothesis_id, created_at DESC);
