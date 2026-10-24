"""
Unit Tests for Parikshak Interoperability, Context Files, and Architecture Layers
==================================================================================
Verifies complete conformance with Parikshak evaluation criteria:
- Review packet hard gate (4 sections in exact order)
- 9 key context files presence and readability
- Layer separation (api, service, model, core)
- CanonicalDB and integration adapter functionality
- Execution pipeline and governance service workflows
"""
import os
import pytest
from fastapi.testclient import TestClient

from api.production import app
from models.schemas import (
    BiotechAuditRequest,
    StrictBaseModel,
    MasterDBIngestRequest,
    MasterDBIngestJob,
    TargetDatabase,
    IngestionFormat,
    IngestionJobStatus
)
from canonical_db.db import CanonicalDB
from canonical_db.integration import MasterDBIntegrationAdapter, ParikshakSyncAdapter
from services.governance_service import GovernanceService
from evaluation_engine.execution_pipeline import BiotechExecutionPipeline
from task_selector.state_machine import GovernanceLifecycleState
from pydantic import ValidationError


client = TestClient(app)


def test_review_packet_hard_gate_compliance():
    """Validates REVIEW_PACKET.md against Parikshak Phase 1 Hard Gate rules."""
    assert os.path.exists("REVIEW_PACKET.md"), "REVIEW_PACKET.md must exist."
    with open("REVIEW_PACKET.md", "r", encoding="utf-8") as f:
        content = f.read()

    # Required headers in exact order
    headers = ["## ENTRY POINT", "## CORE FLOW", "## LIVE FLOW", "## OUTPUT SAMPLE"]
    positions = []
    for h in headers:
        pos = content.find(h)
        assert pos != -1, f"Required header '{h}' not found in REVIEW_PACKET.md"
        positions.append(pos)

    assert positions == sorted(positions), "Headers must appear in exact order."

    # Verify JSON sample contract keys
    assert '"evaluation_result": "PASS"' in content
    assert '"failure_type": null' in content
    assert '"trace_id":' in content


def test_parikshak_context_files_all_present():
    """Ensures all 9 files in Parikshak _CONTEXT_FILES are present and non-empty."""
    context_files = [
        "README.md",
        "REVIEW_PACKET.md",
        "CODE_PACKET.md",
        "api/production.py",
        "api/review_routes.py",
        "evaluation_engine/rule_engine.py",
        "evaluation_engine/execution_pipeline.py",
        "canonical_db/db.py",
        "canonical_db/integration.py",
    ]
    for file_path in context_files:
        assert os.path.exists(file_path), f"Mandatory context file missing: {file_path}"
        assert os.path.getsize(file_path) > 50, f"Context file too small (< 50 bytes): {file_path}"


def test_canonical_db_operations(tmp_path):
    """Tests CanonicalDB event logging and review record persistence."""
    db_file = str(tmp_path / "test_canonical.sqlite")
    journal_file = str(tmp_path / "test_journal.jsonl")
    db = CanonicalDB(db_path=db_file, journal_path=journal_file)

    event = db.append_event(
        event_id="evt-test-1",
        trace_id="trace-test-1",
        actor="Ansh Gupta",
        event_type="test_event",
        payload={"score": 100, "status": "pass"}
    )
    assert event["sequence"] == 1
    assert len(event["event_hash"]) == 64

    # Second event parent hash chaining
    event2 = db.append_event(
        event_id="evt-test-2",
        trace_id="trace-test-2",
        actor="Ansh Gupta",
        event_type="test_event_2",
        payload={"score": 100, "status": "pass"}
    )
    assert event2["sequence"] == 2
    assert event2["parent_event_hash"] == event["event_hash"]

    # Store and retrieve review
    db.store_review("rev-1", "Sara", "pass", 100, "APPROVED", {"notes": "optimal"})
    rec = db.get_review("rev-1")
    assert rec is not None
    assert rec["candidate_id"] == "Sara"
    assert rec["score"] == 100


def test_integration_adapters():
    """Tests MasterDB and Parikshak synchronization adapters with real Ingestion Certification contracts."""
    m_adapter = MasterDBIntegrationAdapter(endpoint_url="http://mock-masterdb:8000")
    ping = m_adapter.ping()
    assert "status" in ping

    # 1. JWT Authentication with Parikshak / MasterDB credentials
    token = m_adapter.generate_auth_token(actor="Ansh", roles=["operator", "ingest:operator", "ingest:relationaldb"])
    assert isinstance(token, str) and len(token) > 20

    p_adapter = ParikshakSyncAdapter()
    token_verification = p_adapter.verify_token(token)
    assert token_verification["valid"] is True
    assert token_verification["payload"]["sub"] == "Ansh"
    assert "ingest:relationaldb" in token_verification["payload"]["roles"]

    # 2. MasterDB Ingest Request to RelationalDB target
    ingest_req = MasterDBIngestRequest(
        dataset_id="DS-BIOTECH-SARA-001",
        target_database=TargetDatabase.RELATIONAL_DB,
        source_format=IngestionFormat.JSON,
        package_id="pkg-biotech-sara-1",
        metadata={"candidate": "Sara", "capability": "Formulation Stability"}
    )
    job = m_adapter.submit_ingest_request(ingest_req, actor="Ansh")
    assert job.dataset_id == "DS-BIOTECH-SARA-001"
    assert job.target_database == TargetDatabase.RELATIONAL_DB
    assert job.status == IngestionJobStatus.PERSISTED
    assert job.integrity_score == 100.0
    assert len(job.steps) == 4
    assert all(s.passed for s in job.steps)

    # 3. Validation and Certification requests
    val = m_adapter.validate_dataset("datasets/sara_formulation.json", dataset_id="DS-BIOTECH-SARA-001")
    assert val["validation_passed"] is True
    assert val["score"] == 100.0

    cert = m_adapter.certify_dataset("DS-BIOTECH-SARA-001")
    assert cert["state"] == "CERTIFIED"
    assert cert["eligible_for_masterdb"] is True

    # 4. Parikshak candidate history sync
    sync = p_adapter.sync_candidate_history("Ansh Gupta", "T-GOV-F01", 100, "APPROVED")
    assert sync["synced"] is True
    assert sync["score"] == 100


def test_governance_service_workflow(tmp_path):
    """Tests GovernanceService audit processing and OCC state transition."""
    gov_service = GovernanceService()
    valid_payload = {
        "candidate": "Sara",
        "formulation_type": "Liposomal Amphotericin B",
        "ph_stability": 7.4,
        "temperature_celsius": 4.0,
        "assay_purity": 99.2,
        "degradation_rate_per_month": 0.001,
        "associated_drugs": ["Amphotericin B", "Doxorubicin"],
        "primary_attributed_drug": "Amphotericin B",
        "is_synthetic": False
    }

    rubric = gov_service.process_audit_submission(
        task_id="T-GOV-F01",
        candidate_name="Sara",
        capability_name="Formulation Stability",
        payload=valid_payload,
        trace_id="trace-gov-service-test-1",
        query_drug="Amphotericin B"
    )
    assert rubric.overall_pass is True
    assert rubric.score >= 90

    # OCC transition
    record = gov_service.execute_occ_transition(
        entity_id="entity-gov-1",
        expected_version=1,
        target_state=GovernanceLifecycleState.VALIDATING,
        actor="Ansh Gupta",
        trace_id="trace-transition-1"
    )
    assert record.state == GovernanceLifecycleState.VALIDATING
    assert record.version == 2


def test_execution_pipeline_evaluation():
    """Tests BiotechExecutionPipeline end-to-end evaluation."""
    pipe = BiotechExecutionPipeline()
    valid_payload = {
        "candidate": "Sara",
        "formulation_type": "Liposomal Amphotericin B",
        "ph_stability": 7.4,
        "temperature_celsius": 4.0,
        "assay_purity": 99.2,
        "degradation_rate_per_month": 0.001,
        "associated_drugs": ["Amphotericin B", "Doxorubicin"],
        "primary_attributed_drug": "Amphotericin B",
        "is_synthetic": False
    }
    result = pipe.execute_evaluation(
        task_id="T-GOV-F01",
        candidate_name="Sara",
        capability_name="Formulation Stability",
        payload=valid_payload,
        trace_id="trace-pipe-test-1",
        query_drug="Amphotericin B"
    )
    assert result["evaluation_result"] == "PASS"
    assert result["score"] >= 90
    assert result["failure_type"] is None


def test_schemas_extra_forbid():
    """Tests that schemas strictly reject extraneous fields (schema_violation prevention)."""
    valid_data = {
        "task_id": "T-GOV-F01",
        "candidate_name": "Sara",
        "capability_name": "Formulation Stability",
        "payload": {"test": "data"}
    }
    req = BiotechAuditRequest(**valid_data)
    assert req.task_id == "T-GOV-F01"

    # Extraneous field must fail validation
    with pytest.raises(ValidationError):
        BiotechAuditRequest(**{**valid_data, "unauthorized_extra_field": "illegal_value"})


def test_api_review_routes():
    """Tests /api/v1/review/evaluate endpoint."""
    headers = {"X-User-Role": "Auditor"}
    payload = {
        "task_id": "T-GOV-F01",
        "candidate_name": "Sara",
        "capability_name": "Formulation Stability",
        "payload": {
            "candidate": "Sara",
            "formulation_type": "Liposomal Amphotericin B",
            "ph_stability": 7.4,
            "temperature_celsius": 4.0,
            "assay_purity": 99.2,
            "degradation_rate_per_month": 0.001,
            "associated_drugs": ["Amphotericin B", "Doxorubicin"],
            "primary_attributed_drug": "Amphotericin B",
            "is_synthetic": False
        },
        "query_drug": "Amphotericin B"
    }
    resp = client.post("/api/v1/review/evaluate", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_result"] == "PASS"
    assert data["composite_score"] >= 90
