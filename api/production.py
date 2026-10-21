"""
MasterDB Ecosystem-Wide Convergence Production API
===================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
Authority: MasterDB Governance & Constitutional Controls

Production-grade FastAPI application with strict Pydantic schemas,
error boundary protection, role-based access control, and deterministic state tracking.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

# Local component imports
from evaluation_engine.rule_engine import (
    MasterDBRuleEngine,
    RuleEvaluationResult,
    DatasetClassification,
    SensitivityLevel,
)
from task_selector.review_orchestrator import (
    MasterDBReviewOrchestrator,
    ReviewStage,
    DecisionState,
    ReviewPacketContract,
)
from integrations.local_llm_client import (
    LocalLLMClient,
    LLMVerificationResponse,
)
from security.middleware import (
    ErrorBoundaryMiddleware,
    UserRole,
    require_role,
    register_used_token,
    is_token_spent,
    reset_spent_tokens,
)

logger = logging.getLogger("masterdb.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Initialize core governance components
rule_engine = MasterDBRuleEngine()
review_orchestrator = MasterDBReviewOrchestrator()
llm_client = LocalLLMClient()

# System startup timestamp
START_TIME = time.time()

# ---------------------------------------------------------------------------
# Strict Pydantic Schema Contracts
# ---------------------------------------------------------------------------

class StrictBaseModel(BaseModel):
    """Base model forbidding unexpected extra attributes for strict schema compliance."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class HealthResponse(StrictBaseModel):
    status: str = Field("healthy", description="System operational status")
    service: str = Field("MasterDB Convergence Engine", description="Microservice identifier")
    task_id: str = Field("T-GOV-F01", description="Assigned governance task ID")
    version: str = Field("2.0.0", description="Production API semantic version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    governance_model: str = Field("BHIV Constitutional Control Matrix", description="Active governance model")
    deterministic_hash: str = Field(..., description="Engine state SHA-256 fingerprint")


class DatasetEvaluationRequest(StrictBaseModel):
    dataset_id: str = Field(..., min_length=3, max_length=128, description="Unique dataset identifier")
    dataset_name: str = Field(..., min_length=2, max_length=256, description="Canonical name of dataset")
    source_system: str = Field(..., min_length=2, max_length=128, description="Originating system or department")
    category: str = Field(..., description="Primary domain classification (e.g., geospatial, financial, operational)")
    schema_contract: Dict[str, Any] = Field(..., description="Data schema contract definition with columns and types")
    records_sample: Optional[List[Dict[str, Any]]] = Field(default=None, description="Sample records for inspection")
    sensitivity_level: SensitivityLevel = Field(default=SensitivityLevel.CONFIDENTIAL, description="Data sensitivity classification")
    owner: str = Field(..., min_length=2, max_length=128, description="Designated data steward or team")
    documentation_uri: Optional[str] = Field(default=None, description="Governance documentation link")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary governance metadata")


class DatasetAuditRequest(StrictBaseModel):
    dataset_id: str = Field(..., min_length=3, max_length=128, description="Target dataset identifier")
    gates_to_check: Optional[List[str]] = Field(default=None, description="Optional subset of canonical gates to run")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Audit parameters")


class AccessCheckRequest(StrictBaseModel):
    actor_role: str = Field(..., description="Role requesting data access")
    dataset_id: str = Field(..., min_length=3, max_length=128, description="Target dataset identifier")
    target_classification: DatasetClassification = Field(..., description="Classification level of dataset")
    requested_action: str = Field(..., description="Operation: READ, WRITE, EXPORT, BULK_INSPECT")
    justification: str = Field(..., min_length=10, description="Business justification for access")
    duration_minutes: int = Field(default=60, ge=5, le=10080, description="Requested access duration")
    purpose_code: str = Field(..., min_length=3, description="Canonical governance purpose code")


class ConvergenceReviewRequest(StrictBaseModel):
    review_id: str = Field(..., min_length=3, max_length=128, description="Review tracking UUID")
    stage: ReviewStage = Field(..., description="Target convergence review stage")
    candidate_name: str = Field(..., min_length=2, max_length=128, description="Candidate or product name")
    dataset_ids: List[str] = Field(..., min_length=1, description="List of dataset identifiers involved")
    section16_acknowledged: bool = Field(default=True, description="Explicit agreement to Section 16 governance rules")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Convergence metadata")


class SemanticValidationRequest(StrictBaseModel):
    text_content: str = Field(..., min_length=5, description="Governance or schema documentation to validate")
    schema_type: str = Field(default="governance_profile", description="Target schema or artifact type")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contextual metadata for validation")


class TokenVerificationRequest(StrictBaseModel):
    token: str = Field(..., min_length=8, description="Authentication or verification token to consume")
    nonce: str = Field(..., min_length=4, description="Unique client nonce")
    purpose: str = Field(default="api_governance_call", description="Declared token consumption purpose")


class StatusResponse(StrictBaseModel):
    active_governance_rules: int = Field(..., description="Number of canonical evaluation rules active")
    registered_datasets: int = Field(..., description="Total audited datasets in state")
    convergence_stages_supported: int = Field(..., description="Number of lifecycle review stages")
    total_spent_tokens: int = Field(..., description="Count of spent tokens prevented from replay")
    deterministic_state_hash: str = Field(..., description="SHA-256 fingerprint of current engine state")


# ---------------------------------------------------------------------------
# FastAPI Application Construction
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MasterDB Ecosystem-Wide Convergence Architecture",
    description="Production API microservice for BHIV MasterDB constitutional governance, data validation, and review orchestration.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Apply CORS & Error Boundary Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorBoundaryMiddleware)


# ---------------------------------------------------------------------------
# Custom Request Validation Error Handler (Strict Schema Compliance)
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format schema validation errors strictly and cleanly without internal trace leaks."""
    errors = []
    for err in exc.errors():
        field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field_path,
            "message": err.get("msg", "Schema validation failure"),
            "type": err.get("type", "value_error"),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "error_type": "SchemaValidationError",
            "status_code": 422,
            "detail": "Inbound request schema violated MasterDB contract specifications.",
            "validation_errors": errors,
            "path": request.url.path,
        }
    )


# ---------------------------------------------------------------------------
# Route Definitions
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System Health"])
@app.get("/api/v1/health", response_model=HealthResponse, tags=["System Health"])
async def get_health() -> HealthResponse:
    """System health check and state verification."""
    state_hash = rule_engine.compute_state_hash()
    return HealthResponse(
        status="healthy",
        service="MasterDB Convergence Engine",
        task_id="T-GOV-F01",
        version="2.0.0",
        uptime_seconds=round(time.time() - START_TIME, 2),
        governance_model="BHIV Constitutional Control Matrix",
        deterministic_hash=state_hash,
    )


@app.post("/api/v1/governance/evaluate", response_model=RuleEvaluationResult, tags=["Governance Evaluation"])
async def evaluate_dataset(
    request: DatasetEvaluationRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD, UserRole.PARIKSHAK_EVALUATOR]))
) -> RuleEvaluationResult:
    """
    Evaluates dataset candidate against MasterDB constitutional governance rules
    and schema eligibility gates.
    """
    result = rule_engine.evaluate_dataset_candidate(
        dataset_id=request.dataset_id,
        dataset_name=request.dataset_name,
        source_system=request.source_system,
        category=request.category,
        schema_contract=request.schema_contract,
        records_sample=request.records_sample,
        sensitivity=request.sensitivity_level,
        owner=request.owner,
        metadata=request.metadata,
    )
    return result


@app.post("/api/v1/governance/audit", tags=["Governance Evaluation"])
async def audit_dataset_gates(
    request: DatasetAuditRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> Dict[str, Any]:
    """
    Performs full 10-gate canonical audit for a specified dataset.
    """
    gate_results = rule_engine.evaluate_canonical_gates(
        dataset_id=request.dataset_id,
        metadata=request.metadata,
    )
    all_passed = all(g.get("passed", False) for g in gate_results)
    state_hash = rule_engine.compute_state_hash()
    
    return {
        "dataset_id": request.dataset_id,
        "all_gates_passed": all_passed,
        "gates_evaluated_count": len(gate_results),
        "gate_results": gate_results,
        "deterministic_hash": state_hash,
        "status": "APPROVED" if all_passed else "REJECTED_GATES_FAILED",
    }


@app.post("/api/v1/governance/access-check", tags=["Constitutional Access Control"])
async def check_governed_access(
    request: AccessCheckRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.CONSUMER, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> Dict[str, Any]:
    """
    Constitutional 6-Tuple Access Control Check.
    Validates actor, classification, action, justification, and duration.
    """
    result = rule_engine.evaluate_access_request(
        actor_role=request.actor_role,
        dataset_id=request.dataset_id,
        target_classification=request.target_classification,
        requested_action=request.requested_action,
        justification=request.justification,
        duration_minutes=request.duration_minutes,
        purpose_code=request.purpose_code,
    )
    return result


@app.post("/api/v1/convergence/review", response_model=ReviewPacketContract, tags=["Convergence Orchestration"])
async def review_convergence_stage(
    request: ConvergenceReviewRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD, UserRole.PARIKSHAK_EVALUATOR]))
) -> ReviewPacketContract:
    """
    Executes a formal 9-stage convergence review stage or Section 16 verification.
    """
    packet = review_orchestrator.execute_review_stage(
        review_id=request.review_id,
        stage=request.stage,
        candidate_name=request.candidate_name,
        dataset_ids=request.dataset_ids,
        section16_acknowledged=request.section16_acknowledged,
        metadata=request.metadata,
    )
    return packet


@app.post("/api/v1/semantic/validate", response_model=LLMVerificationResponse, tags=["Semantic Validation"])
async def validate_semantics(
    request: SemanticValidationRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> LLMVerificationResponse:
    """
    Performs deterministic offline semantic validation and entity extraction via Local LLM client.
    """
    response = llm_client.audit_schema_semantics(
        text_content=request.text_content,
        schema_type=request.schema_type,
        context=request.context,
    )
    return response


@app.post("/api/v1/governance/token/verify", tags=["Security & Replay Protection"])
async def verify_governance_token(
    request: TokenVerificationRequest,
) -> Dict[str, Any]:
    """
    Registers and verifies a one-time governance action token to prevent replay attacks.
    """
    register_used_token(
        token=request.token,
        metadata={"nonce": request.nonce, "purpose": request.purpose}
    )
    return {
        "token_prefix": request.token[:8] + "...",
        "verified": True,
        "nonce": request.nonce,
        "replay_prevented": True,
        "message": "Token accepted and permanently marked as spent.",
    }


@app.get("/api/v1/governance/status", response_model=StatusResponse, tags=["Governance Status"])
async def get_governance_status() -> StatusResponse:
    """Retrieves operational status and metrics of MasterDB Governance Engine."""
    from security.middleware import _SPENT_TOKENS
    return StatusResponse(
        active_governance_rules=10,
        registered_datasets=len(rule_engine.dataset_registry),
        convergence_stages_supported=len(ReviewStage),
        total_spent_tokens=len(_SPENT_TOKENS),
        deterministic_state_hash=rule_engine.compute_state_hash(),
    )


# Clean shutdown and reset helper (for test runners)
@app.post("/api/v1/governance/reset", tags=["System Internal"])
async def reset_engine_state(
    current_role: str = Depends(require_role([UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> Dict[str, str]:
    """Resets in-memory registries for clean test execution."""
    rule_engine.dataset_registry.clear()
    reset_spent_tokens()
    return {"status": "reset_completed"}
