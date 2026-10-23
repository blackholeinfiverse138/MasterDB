"""
Biotech Review & Evaluation API Routes
======================================
Exposes standard review endpoints, evaluation pipelines, and Section 16 dispute registries.
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from models.schemas import (
    BiotechAuditRequest,
    BiotechEvaluationRequest,
    DisagreementRecordRequest,
    HealthResponse,
    MetricsResponse,
)
from evaluation_engine.rule_engine import BiotechRuleEngine, EvaluationRubric
from evaluation_engine.execution_pipeline import execution_pipeline
from task_selector.review_orchestrator import (
    BiotechReviewOrchestrator,
    CandidateReviewRecord,
    ReviewStage,
    DecisionState,
)
from security.middleware import UserRole, require_role

router = APIRouter(prefix="/api/v1/review", tags=["Biotech Review Routes"])
rule_engine = BiotechRuleEngine()
orchestrator = BiotechReviewOrchestrator()


@router.post("/evaluate", response_model=EvaluationRubric)
def evaluate_submission(
    request: BiotechAuditRequest,
    role: UserRole = Depends(require_role([UserRole.AUDITOR, UserRole.GOVERNOR, UserRole.ANSH_AUDIT_LEAD, UserRole.REVIEWER]))
) -> EvaluationRubric:
    """Executes deterministic audit evaluation on candidate payload."""
    return rule_engine.evaluate_candidate_submission(
        task_id=request.task_id,
        candidate_name=request.candidate_name,
        capability_name=request.capability_name,
        payload=request.payload,
        query_drug=request.query_drug
    )


@router.post("/pipeline/execute", response_model=Dict[str, Any])
def execute_pipeline(
    request: BiotechAuditRequest,
    trace_id: str = "trace-direct-api-call",
    role: UserRole = Depends(require_role([UserRole.AUDITOR, UserRole.GOVERNOR, UserRole.ANSH_AUDIT_LEAD]))
) -> Dict[str, Any]:
    """Runs complete end-to-end execution pipeline."""
    return execution_pipeline.execute_evaluation(
        task_id=request.task_id,
        candidate_name=request.candidate_name,
        capability_name=request.capability_name,
        payload=request.payload,
        trace_id=trace_id,
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
    role: UserRole = Depends(require_role([UserRole.AUDITOR, UserRole.GOVERNOR, UserRole.ANSH_AUDIT_LEAD]))
) -> CandidateReviewRecord:
    """Registers Section 16 independent audit disagreement."""
    return orchestrator.record_disagreement(
        candidate_id=request.candidate_id,
        raised_by=request.raised_by,
        reason=request.reason,
        dissenting_view=request.dissenting_view
    )
