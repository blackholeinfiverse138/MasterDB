"""
MasterDB Convergence Review & Evaluation API Routes
===================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
Authority: MasterDB Data Governance & Constitutional Controls

Exposes standard review endpoints, execution pipelines, Section 16 dispute registries,
and deterministic evaluation interfaces for the Parikshak evaluation system.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from models.schemas import (
    MasterDBAuditRequest,
    MasterDBEvaluationRequest,
    BiotechAuditRequest,
    BiotechEvaluationRequest,
    DisagreementRecordRequest,
    HealthResponse,
    MetricsResponse,
)
from evaluation_engine.rule_engine import MasterDBRuleEngine, EvaluationRubric, BiotechRuleEngine
from evaluation_engine.execution_pipeline import execution_pipeline, MasterDBExecutionPipeline
from task_selector.review_orchestrator import (
    MasterDBReviewOrchestrator,
    CandidateReviewRecord,
    ReviewStage,
    DecisionState,
    BiotechReviewOrchestrator,
)
from security.middleware import UserRole, require_role

router = APIRouter(prefix="/api/v1/review", tags=["MasterDB Review Routes"])
rule_engine = MasterDBRuleEngine()
orchestrator = MasterDBReviewOrchestrator()


@router.post("/evaluate", response_model=EvaluationRubric)
def evaluate_submission(
    request: MasterDBAuditRequest,
    role: UserRole = Depends(require_role([UserRole.AUDITOR, UserRole.GOVERNOR, UserRole.ANSH_AUDIT_LEAD, UserRole.REVIEWER, UserRole.MASTERDB_ADMIN, UserRole.PARIKSHAK_EVALUATOR]))
) -> EvaluationRubric:
    """Executes deterministic audit evaluation on candidate payload."""
    return rule_engine.evaluate_candidate_submission(
        task_id=request.task_id,
        candidate_name=request.candidate_name,
        capability_name=request.capability_name,
        payload=request.payload,
        governance_dimension=request.governance_dimension,
        query_drug=request.query_drug
    )


@router.post("/pipeline/execute", response_model=Dict[str, Any])
def execute_pipeline(
    request: MasterDBAuditRequest,
    trace_id: str = "trace-direct-api-call",
    role: UserRole = Depends(require_role([UserRole.AUDITOR, UserRole.GOVERNOR, UserRole.ANSH_AUDIT_LEAD, UserRole.MASTERDB_ADMIN]))
) -> Dict[str, Any]:
    """Runs complete end-to-end execution pipeline."""
    return execution_pipeline.execute_evaluation(
        task_id=request.task_id,
        candidate_name=request.candidate_name,
        capability_name=request.capability_name,
        payload=request.payload,
        trace_id=trace_id,
        governance_dimension=request.governance_dimension,
        query_drug=request.query_drug
    )


@router.get("/candidate/{candidate_id}", response_model=Dict[str, Any])
def get_candidate_review_status(candidate_id: str) -> Dict[str, Any]:
    """Retrieves active candidate review record."""
    record = orchestrator.candidate_reviews.get(candidate_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate '{candidate_id}' not found.")
    return record.model_dump()


@router.post("/disagreement", response_model=CandidateReviewRecord)
def record_disagreement(
    request: DisagreementRecordRequest,
    role: UserRole = Depends(require_role([UserRole.AUDITOR, UserRole.GOVERNOR, UserRole.ANSH_AUDIT_LEAD, UserRole.MASTERDB_ADMIN]))
) -> CandidateReviewRecord:
    """Registers Section 16 independent audit disagreement."""
    return orchestrator.record_disagreement(
        candidate_id=request.candidate_id,
        raised_by=request.raised_by,
        reason=request.reason,
        dissenting_view=request.dissenting_view
    )


@router.get("/health", response_model=HealthResponse)
def get_review_health() -> HealthResponse:
    """Returns review subsystem health status and capabilities."""
    return HealthResponse(
        status="healthy",
        service="MasterDB Convergence Review Engine",
        timestamp=datetime.now(timezone.utc).isoformat(),
        active_capabilities=[
            "Deterministic Rule Evaluation",
            "9-Stage Convergence Lifecycle",
            "Section 16 Disagreement Ledger",
            "Pravah Replay Integration",
            "Optimistic Concurrency Control"
        ],
        error_boundary_active=True
    )


@router.get("/stages", response_model=List[str])
def list_review_stages() -> List[str]:
    """Lists the 9 standard Day 3 review stages."""
    return [stage.value for stage in ReviewStage]


# Backward compatibility production alias
@router.post("/production/audit", response_model=EvaluationRubric, include_in_schema=False)
@router.post("/production/biotech/audit", response_model=EvaluationRubric, include_in_schema=False)
def legacy_audit_alias(
    request: MasterDBAuditRequest,
    role: UserRole = Depends(require_role([UserRole.AUDITOR, UserRole.GOVERNOR, UserRole.ANSH_AUDIT_LEAD, UserRole.REVIEWER]))
) -> EvaluationRubric:
    """Legacy backward-compatible audit endpoint."""
    return evaluate_submission(request=request, role=role)
