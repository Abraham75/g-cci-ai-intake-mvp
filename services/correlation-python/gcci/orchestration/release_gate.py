from __future__ import annotations

from .models import FindingSeverity, ReleaseDecision, ReviewFinding, TaskBrief


def evaluate_release(
    *,
    findings: list[ReviewFinding],
    tasks: list[TaskBrief],
    approved_task_ids: set[str],
) -> ReleaseDecision:
    critical = sum(
        1
        for finding in findings
        if finding.severity == FindingSeverity.CRITICAL and not finding.resolved
    )
    major = sum(
        1
        for finding in findings
        if finding.severity == FindingSeverity.MAJOR and not finding.resolved
    )
    missing_approval = any(
        task.requires_human_approval and task.task_id not in approved_task_ids for task in tasks
    )

    reasons: list[str] = []
    if critical:
        reasons.append(f"{critical} unresolved Critical review finding(s)")
    if missing_approval:
        reasons.append("required human approval is missing")
    if not reasons:
        reasons.append("release gates satisfied")

    return ReleaseDecision(
        releasable=critical == 0 and not missing_approval,
        reasons=reasons,
        unresolved_critical=critical,
        unresolved_major=major,
        human_approval_missing=missing_approval,
    )
