import pytest

from gcci.orchestration.graph import TaskGraphError, ready_tasks, validate_task_graph
from gcci.orchestration.models import (
    AgentRole,
    Claim,
    ClaimStatus,
    FindingSeverity,
    ReviewFinding,
    TaskBrief,
)
from gcci.orchestration.release_gate import evaluate_release


def task(task_id: str, *, depends_on=None, approval=False):
    return TaskBrief(
        task_id=task_id,
        role=AgentRole.TECHNICAL_SPECIALIST,
        objective=f"execute {task_id}",
        required_output="implementation artifact",
        quality_bar="tests and explicit risks",
        depends_on=depends_on or [],
        requires_human_approval=approval,
    )


def test_verified_claim_requires_evidence():
    with pytest.raises(ValueError):
        Claim(statement="production ready", status=ClaimStatus.VERIFIED)

    claim = Claim(
        statement="migration applied in CI",
        status=ClaimStatus.VERIFIED,
        evidence_ids=["ci-run-123"],
    )
    assert claim.evidence_ids == ["ci-run-123"]


def test_graph_orders_dependencies_and_exposes_parallel_ready_tasks():
    tasks = [task("T3", depends_on=["T1"]), task("T1"), task("T2")]
    order = validate_task_graph(tasks)
    assert order.index("T1") < order.index("T3")
    assert {item.task_id for item in ready_tasks(tasks, set())} == {"T1", "T2"}


def test_graph_rejects_cycles():
    with pytest.raises(TaskGraphError):
        validate_task_graph([task("T1", depends_on=["T2"]), task("T2", depends_on=["T1"])])


def test_critical_red_team_finding_blocks_release():
    decision = evaluate_release(
        findings=[
            ReviewFinding(
                severity=FindingSeverity.CRITICAL,
                issue="outreach can bypass compliance",
                proposed_fix="require durable compliance gate",
            )
        ],
        tasks=[task("T1")],
        approved_task_ids=set(),
    )
    assert decision.releasable is False
    assert decision.unresolved_critical == 1


def test_sensitive_task_requires_human_approval():
    sensitive = task("CONTACT", approval=True)
    blocked = evaluate_release(findings=[], tasks=[sensitive], approved_task_ids=set())
    allowed = evaluate_release(findings=[], tasks=[sensitive], approved_task_ids={"CONTACT"})
    assert blocked.releasable is False
    assert blocked.human_approval_missing is True
    assert allowed.releasable is True
