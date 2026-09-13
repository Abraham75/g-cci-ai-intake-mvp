from gcci.lead_qualification import RESOLUTION_TASKS, _priority, _qualification_decision


def canonical_input(
    *,
    injury: float = 0.8,
    liability: float = 0.8,
    collectability: float = 0.8,
    evidence: float = 0.7,
    defendant_resolution: float = 0.6,
    high_contradictions: int = 0,
) -> dict:
    return {
        "scores": {
            "injury": injury,
            "liability": liability,
            "collectability": collectability,
            "evidence": evidence,
            "defendantResolution": defendant_resolution,
        },
        "contradictions": {
            "highSeverityUnresolved": high_contradictions,
            "other": 0,
        },
    }


def test_high_value_case_stops_at_qualified_case_until_claimant_verified():
    decision = _qualification_decision(
        score=0.86,
        tier="A",
        canonical_input=canonical_input(),
        claimant_stage="CORROBORATED",
    )
    assert decision["caseQualified"] is True
    assert decision["stage"] == "S2_QUALIFIED_CASE"
    assert any("VERIFIED" in action for action in decision["requiredActions"])


def test_verified_claimant_can_advance_to_resolved_prospect_but_not_outreach_ready():
    decision = _qualification_decision(
        score=0.86,
        tier="A",
        canonical_input=canonical_input(),
        claimant_stage="VERIFIED",
    )
    assert decision["caseQualified"] is True
    assert decision["stage"] == "S3_RESOLVED_PROSPECT"
    assert any("compliance gate" in action.lower() for action in decision["requiredActions"])


def test_high_severity_contradiction_blocks_qualified_case():
    decision = _qualification_decision(
        score=0.84,
        tier="C",
        canonical_input=canonical_input(high_contradictions=1),
        claimant_stage="VERIFIED",
    )
    assert decision["caseQualified"] is False
    assert decision["stage"] == "S1_OPPORTUNITY"
    assert any("high-severity contradiction" in blocker.lower() for blocker in decision["blockers"])


def test_weak_injury_or_collectability_does_not_qualify_even_with_moderate_cos():
    decision = _qualification_decision(
        score=0.70,
        tier="B",
        canonical_input=canonical_input(injury=0.2, collectability=0.3),
        claimant_stage="UNKNOWN",
    )
    assert decision["caseQualified"] is False
    assert decision["stage"] == "S1_OPPORTUNITY"


def test_official_crash_report_is_highest_priority_resolution_source():
    ranked = sorted(RESOLUTION_TASKS, key=_priority, reverse=True)
    assert ranked[0].source_type == "OFFICIAL_CRASH_REPORT"
    assert _priority(ranked[0]) > _priority(ranked[-1])
