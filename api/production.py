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
from evaluation_engine.pravah_streaming import (
    PravahEventType,
    PravahEvent,
    PravahReplayEngine,
)
from task_selector.state_machine import (
    GovernanceLifecycleState,
    ConcurrencyRecord,
    ConcurrencyGovernanceEngine,
    OCCConflictError,
    InvalidStateTransitionError,
)
from integrations.fin_vana_integrator import (
    FinVanaIntegrationEngine,
    CarbonUnderwritingRequest,
    CarbonUnderwritingResult,
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
pravah_engine = PravahReplayEngine()
concurrency_engine = ConcurrencyGovernanceEngine(pravah_engine=pravah_engine)
fin_vana_engine = FinVanaIntegrationEngine()

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



class ParikshakReviewUpdateRequest(StrictBaseModel):
    review_reference: str = Field(..., description="Canonical review reference ID")
    task_id: str = Field(..., description="Evaluated task ID")
    candidate_id: str = Field(..., description="Candidate or agent identifier")
    score: int = Field(..., ge=0, le=100, description="Evaluation score")
    readiness_percentage: float = Field(..., ge=0.0, le=100.0, description="Readiness percentage")
    review_summary: str = Field(..., description="Executive review summary")
    timeline_commentary: Optional[str] = Field(default=None, description="Timeline notes")
    next_task_reference: Optional[str] = Field(default=None, description="Assigned next task ID")
    trace_id: str = Field(..., description="Cryptographic audit trace ID")


class ParikshakCandidateHistoryRequest(StrictBaseModel):
    candidate_id: str = Field(..., description="Candidate or agent identifier")
    task_id: str = Field(..., description="Evaluated task ID")
    evaluation_result: str = Field(..., description="PASS, BORDERLINE, or FAIL")
    score: int = Field(..., ge=0, le=100, description="Evaluation score")
    next_task_id: Optional[str] = Field(default=None, description="Successor task ID")


class VanaForestCoverQueryRequest(StrictBaseModel):
    consumer_actor: str = Field(..., min_length=2, max_length=128, description="Requesting consumer (e.g., VANA, FIN)")
    district: Optional[str] = Field(default=None, description="Optional Maharashtra district filter (e.g. Pune, Thane, Ratnagiri)")
    purpose: str = Field(default="DISTRICT_CANOPY_ANALYSIS", description="Declared governance purpose")


class VanaMangroveQueryRequest(StrictBaseModel):
    consumer_actor: str = Field(..., min_length=2, max_length=128, description="Requesting consumer (e.g., VANA, FIN)")
    zone_query: Optional[str] = Field(default=None, description="Optional sanctuary zone filter (e.g. Airoli, Vashi, Bhandup)")
    purpose: str = Field(default="BLUE_CARBON_QUANTIFICATION", description="Declared governance purpose")


# Global In-Memory Sync Ledgers for Parikshak
_PARIKSHAK_REVIEWS_LEDGER: List[Dict[str, Any]] = []
_PARIKSHAK_CANDIDATE_HISTORY: List[Dict[str, Any]] = []


class PravahStreamEventRequest(StrictBaseModel):
    trace_id: str = Field(..., min_length=4, max_length=128, description="Distributed trace ID")
    event_type: PravahEventType = Field(..., description="Canonical Pravah event type")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    source_system: str = Field(default="MASTERDB", min_length=2, max_length=64, description="Originating system")
    destination: str = Field(default="PRAVAH_REPLAY_LEDGER", min_length=2, max_length=64, description="Target subsystem")


class PravahReplayRequest(StrictBaseModel):
    from_sequence: int = Field(default=1, ge=1, description="Start sequence for replay")
    to_sequence: Optional[int] = Field(default=None, ge=1, description="End sequence for replay")


class ConcurrencyTransitionRequest(StrictBaseModel):
    entity_id: str = Field(..., min_length=3, max_length=128, description="Unique entity identifier")
    expected_version: int = Field(..., ge=1, description="Expected OCC record version")
    target_state: GovernanceLifecycleState = Field(..., description="Target DFA lifecycle state")
    actor: str = Field(..., min_length=2, max_length=64, description="Transition operator")
    trace_id: str = Field(..., min_length=4, max_length=128, description="Trace identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary transition metadata")


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

from api.review_routes import router as review_router
app.include_router(review_router)


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


# ---------------------------------------------------------------------------
# Pravah Asynchronous Streaming & Replay Ledger Endpoints (T-GOV-002)
# ---------------------------------------------------------------------------

@app.post("/api/v1/pravah/stream", response_model=PravahEvent, tags=["Pravah Replay Ledger"])
async def stream_pravah_event(
    request: PravahStreamEventRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD, UserRole.CONSUMER]))
) -> PravahEvent:
    """Streams an event to the append-only Pravah replay ledger with cryptographic hash chaining."""
    event = pravah_engine.append_event(
        trace_id=request.trace_id,
        event_type=request.event_type,
        payload=request.payload,
        source_system=request.source_system,
        destination=request.destination
    )
    return event


@app.post("/api/v1/pravah/replay", response_model=List[PravahEvent], tags=["Pravah Replay Ledger"])
async def replay_pravah_events(
    request: PravahReplayRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD, UserRole.CONSUMER]))
) -> List[PravahEvent]:
    """Replays events deterministically from specified sequence range."""
    return pravah_engine.replay(from_sequence=request.from_sequence, to_sequence=request.to_sequence)


@app.get("/api/v1/pravah/integrity", tags=["Pravah Replay Ledger"])
async def verify_pravah_integrity() -> Dict[str, Any]:
    """Verifies cryptographic hash continuity and monotonic sequencing of Pravah replay ledger."""
    return pravah_engine.verify_integrity()


# ---------------------------------------------------------------------------
# Strict Concurrency Control (OCC) & DFA State Machine Endpoints (T-GOV-002)
# ---------------------------------------------------------------------------

@app.post("/api/v1/governance/concurrency/transition", response_model=ConcurrencyRecord, tags=["Concurrency Governance"])
async def transition_concurrency_state(
    request: ConcurrencyTransitionRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> ConcurrencyRecord:
    """
    Executes an Optimistic Concurrency Control (OCC) protected state transition.
    Returns 409 Conflict if expected version does not match current version.
    Returns 422 Unprocessable if attempted transition violates DFA rules.
    """
    try:
        record = concurrency_engine.transition_state(
            entity_id=request.entity_id,
            expected_version=request.expected_version,
            target_state=request.target_state,
            actor=request.actor,
            trace_id=request.trace_id,
            metadata=request.metadata
        )
        return record
    except OCCConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message
        )


@app.get("/api/v1/governance/concurrency/state/{entity_id}", tags=["Concurrency Governance"])
async def get_concurrency_state(entity_id: str) -> Dict[str, Any]:
    """Retrieves current OCC state, version, and transition hash for a governance entity."""
    record = concurrency_engine.get_entity_state(entity_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found in concurrency governance registry."
        )
    return record.model_dump()


# Clean shutdown and reset helper (for test runners)

# ---------------------------------------------------------------------------
# Parikshak Integration Sync Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/masterdb/reviews/update", tags=["Parikshak Sync"])
async def update_task_review_record(request: ParikshakReviewUpdateRequest) -> Dict[str, Any]:
    """Ingests and records canonical engineering review summaries from Parikshak."""
    record = request.model_dump()
    record["received_at"] = time.time()
    _PARIKSHAK_REVIEWS_LEDGER.append(record)
    return {
        "status": "SUCCESS",
        "message": f"Review {request.review_reference} recorded in MasterDB",
        "review_reference": request.review_reference,
        "score": request.score,
        "sync_status": "SYNCED"
    }


@app.post("/api/v1/masterdb/candidate/history", tags=["Parikshak Sync"])
async def update_candidate_history(request: ParikshakCandidateHistoryRequest) -> Dict[str, Any]:
    """Ingests and records candidate progression history from Parikshak."""
    record = request.model_dump()
    record["received_at"] = time.time()
    _PARIKSHAK_CANDIDATE_HISTORY.append(record)
    return {
        "status": "SUCCESS",
        "message": f"Candidate history for {request.candidate_id} recorded in MasterDB",
        "candidate_id": request.candidate_id,
        "sync_status": "SYNCED"
    }


@app.post("/api/v1/integration/vana/forest-cover/query", tags=["VANA Real Data Integration"])
async def query_vana_forest_cover(
    request: VanaForestCoverQueryRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.CONSUMER, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> Dict[str, Any]:
    """Queries real FSI ISFR 2023 Maharashtra forest cover records with MDU ontology metadata."""
    try:
        return fin_vana_engine.query_vana_forest_cover(
            consumer_actor=request.consumer_actor,
            district=request.district,
            purpose=request.purpose
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.post("/api/v1/integration/vana/mangrove-biomass/query", tags=["VANA Real Data Integration"])
async def query_vana_mangrove_biomass(
    request: VanaMangroveQueryRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.CONSUMER, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> Dict[str, Any]:
    """Queries real Thane Creek mangrove above-ground biomass records with allometric survey data."""
    try:
        return fin_vana_engine.query_vana_mangrove_biomass(
            consumer_actor=request.consumer_actor,
            zone_query=request.zone_query,
            purpose=request.purpose
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.post("/api/v1/integration/fin/carbon-underwrite", response_model=CarbonUnderwritingResult, tags=["FIN Real Data Integration"])
async def execute_fin_carbon_underwriting(
    request: CarbonUnderwritingRequest,
    current_role: str = Depends(require_role([UserRole.GOVERNOR, UserRole.AUDITOR, UserRole.STEWARD, UserRole.CONSUMER, UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> CarbonUnderwritingResult:
    """Executes real ESG carbon underwriting calculation over MasterDB canonical records."""
    try:
        return fin_vana_engine.execute_fin_carbon_underwriting(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.get("/api/v1/integration/fin-vana/catalog", tags=["FIN / VANA Real Data Integration"])
async def get_fin_vana_catalog() -> Dict[str, Any]:
    """Returns the full catalog of integrated real datasets and supported capabilities for FIN and VANA."""
    return fin_vana_engine.get_catalog()


@app.post("/api/v1/governance/reset", tags=["System Internal"])
async def reset_engine_state(
    current_role: str = Depends(require_role([UserRole.MASTERDB_ADMIN, UserRole.ANSH_GOV_LEAD]))
) -> Dict[str, str]:
    """Resets in-memory registries for clean test execution."""
    rule_engine.dataset_registry.clear()
    reset_spent_tokens()
    pravah_engine.reset_for_tests()
    concurrency_engine.reset_for_tests()
    fin_vana_engine.underwriting_ledger.clear()
    return {"status": "reset_completed"}
