from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AgentRole(StrEnum):
    ORCHESTRATOR = "ORCHESTRATOR"
    RESEARCHER = "RESEARCHER"
    ANALYST = "ANALYST"
    WRITER = "WRITER"
    TECHNICAL_SPECIALIST = "TECHNICAL_SPECIALIST"
    CRITIC = "CRITIC"
    EDITOR = "EDITOR"


class ClaimStatus(StrEnum):
    VERIFIED = "Verified"
    INFERRED = "Inferred"
    ASSUMED = "Assumed"
    OPINION = "Opinion"


class TaskState(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class FindingSeverity(StrEnum):
    CRITICAL = "Critical"
    MAJOR = "Major"
    MINOR = "Minor"


class Claim(BaseModel):
    statement: str = Field(min_length=1, max_length=8000)
    status: ClaimStatus
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def verified_requires_evidence(self):
        if self.status == ClaimStatus.VERIFIED and not self.evidence_ids:
            raise ValueError("Verified claims require at least one evidence ID")
        return self


class TaskBrief(BaseModel):
    task_id: str = Field(min_length=1, max_length=64)
    role: AgentRole
    objective: str = Field(min_length=1, max_length=4000)
    context: str = Field(default="", max_length=12000)
    inputs: list[str] = Field(default_factory=list)
    required_output: str = Field(min_length=1, max_length=8000)
    quality_bar: str = Field(min_length=1, max_length=4000)
    constraints: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    questions_or_assumptions: list[str] = Field(default_factory=list)
    requires_human_approval: bool = False


class AgentHandoff(BaseModel):
    task_id: str
    role: AgentRole
    objective: str
    inputs: list[str] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    unresolved_questions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_next_task: str | None = None


class ReviewFinding(BaseModel):
    severity: FindingSeverity
    issue: str
    proposed_fix: str
    evidence_ids: list[str] = Field(default_factory=list)
    resolved: bool = False


class ReleaseDecision(BaseModel):
    releasable: bool
    reasons: list[str]
    unresolved_critical: int = 0
    unresolved_major: int = 0
    human_approval_missing: bool = False
