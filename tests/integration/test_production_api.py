"""
Integration Tests - MasterDB Production API Microservice
=========================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoints(client: TestClient):
    # Test root health
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["task_id"] == "T-GOV-F01"
    assert "deterministic_hash" in data
    assert len(data["deterministic_hash"]) == 64

    # Test v1 health
    resp_v1 = client.get("/api/v1/health")
    assert resp_v1.status_code == 200
    assert resp_v1.json()["service"] == "MasterDB Convergence Engine"


def test_evaluate_dataset_endpoint_valid(client: TestClient, valid_dataset_payload):
    headers = {"X-Role": "governor"}
    resp = client.post("/api/v1/governance/evaluate", json=valid_dataset_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["score"] == 100.0
    assert data["rule_id"] == "R-GOV-INGEST-01"


def test_evaluate_dataset_endpoint_synthetic_quarantine(client: TestClient, synthetic_dataset_payload):
    headers = {"X-Role": "governor"}
    resp = client.post("/api/v1/governance/evaluate", json=synthetic_dataset_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["rule_id"] == "R-QUARANTINE-01"
    assert "Quarantined" in data["observation"]


def test_evaluate_dataset_strict_schema_validation_rejection(client: TestClient):
    headers = {"X-Role": "governor"}
    # Malformed payload: missing dataset_name, source_system, category, etc.
    invalid_payload = {
        "dataset_id": "DS-INVALID",
        "unexpected_extra_field": "disallowed_by_strict_schema"
    }
    resp = client.post("/api/v1/governance/evaluate", json=invalid_payload, headers=headers)
    assert resp.status_code == 422
    data = resp.json()
    assert data["status"] == "error"
    assert data["error_type"] == "SchemaValidationError"
    assert "validation_errors" in data
    assert len(data["validation_errors"]) > 0


def test_dataset_audit_ten_canonical_gates(client: TestClient):
    headers = {"X-Role": "governor"}
    audit_payload = {
        "dataset_id": "masterdb.spatial.survey_of_india.boundaries",
        "metadata": {
            "owner": "Survey of India",
            "source": "Official Gazette",
            "provenance": "Direct Cadastral Extraction",
            "schema": {"type": "polygon"},
            "classification": "CANONICAL",
            "quality_status": "VALIDATED",
            "allowed_consumers": ["BharatMala-GIS", "VANA"],
            "intended_use": "National Infrastructure Planning",
            "lifecycle_status": "ACTIVE",
            "approval_authority": "Ansh Gupta (Governance Lead)",
        }
    }
    resp = client.post("/api/v1/governance/audit", json=audit_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["all_gates_passed"] is True
    assert data["gates_evaluated_count"] == 10
    assert data["status"] == "APPROVED"
    assert len(data["deterministic_hash"]) == 64


def test_governance_access_check(client: TestClient):
    headers = {"X-Role": "consumer"}
    access_payload = {
        "actor_role": "VANA",
        "dataset_id": "DS-FSI-ISFR-2023-FOREST-COVER",
        "target_classification": "CANONICAL",
        "requested_action": "READ",
        "justification": "Evaluating regional carbon offset baseline metrics for Maharashtra corridor.",
        "duration_minutes": 120,
        "purpose_code": "DISTRICT_CANOPY_ANALYSIS",
    }
    resp = client.post("/api/v1/governance/access-check", json=access_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True
    assert data["decision"] == "ALLOWED"


def test_convergence_review_stage_with_section16_handling(client: TestClient):
    headers = {"X-Role": "governor"}
    
    # 1. Acknowledged Section 16 -> APPROVED
    req_approved = {
        "review_id": "REV-2026-CONV-001",
        "stage": "Stage 3: Independent Governance Audit (Ansh Gupta)",
        "candidate_name": "Ansh Gupta",
        "dataset_ids": ["DS-FSI-ISFR-2023-FOREST-COVER"],
        "section16_acknowledged": True,
    }
    resp1 = client.post("/api/v1/convergence/review", json=req_approved, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["decision_state"] == "APPROVED"
    assert data1["candidate_name"] == "Ansh Gupta"

    # 2. Unacknowledged Section 16 -> REVISION REQUIRED
    req_rejected = {
        "review_id": "REV-2026-CONV-002",
        "stage": "Stage 3: Independent Governance Audit (Ansh Gupta)",
        "candidate_name": "Unverified Candidate",
        "dataset_ids": ["DS-FSI-ISFR-2023-FOREST-COVER"],
        "section16_acknowledged": False,
    }
    resp2 = client.post("/api/v1/convergence/review", json=req_rejected, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["decision_state"] == "REVISION REQUIRED"
    assert len(data2["disagreements"]) > 0


def test_semantic_validate_endpoint(client: TestClient):
    headers = {"X-Role": "auditor"}
    payload = {
        "text_content": "MasterDB canonical spatial dataset referenced by MDU ontology schema.",
        "schema_type": "spatial_profile",
        "context": {"domain": "geospatial"}
    }
    resp = client.post("/api/v1/semantic/validate", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert "CANONICAL" in data["extracted_entities"]
    assert "MASTERDB" in data["extracted_entities"]


def test_token_verify_and_replay_prevention_api(client: TestClient):
    token_str = "auth_tok_parikshak_verifier_123456789"
    payload = {
        "token": token_str,
        "nonce": "nonce_abc123",
        "purpose": "parikshak_eval_run"
    }
    # First attempt: succeeds
    resp1 = client.post("/api/v1/governance/token/verify", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["verified"] is True

    # Immediate replay: rejected with 409 Conflict
    resp2 = client.post("/api/v1/governance/token/verify", json=payload)
    assert resp2.status_code == 409
    assert resp2.json()["status"] == "error"
    assert "Token replay detected" in resp2.json()["detail"]


def test_governance_status_endpoint(client: TestClient):
    resp = client.get("/api/v1/governance/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_governance_rules"] == 10
    assert data["convergence_stages_supported"] == 9
    assert len(data["deterministic_state_hash"]) == 64


def test_engine_reset_endpoint(client: TestClient):
    headers = {"X-Role": "ansh_gov_lead"}
    resp = client.post("/api/v1/governance/reset", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "reset_completed"


def test_error_boundary_middleware_catches_all_exceptions(client: TestClient):
    # Request with invalid non-JSON body to an endpoint expecting JSON
    resp = client.post(
        "/api/v1/governance/evaluate",
        content="malformed non-json body {{{",
        headers={"Content-Type": "application/json", "X-Role": "governor"}
    )
    # Must be handled cleanly by FastAPI / ErrorBoundaryMiddleware without 500 crash
    assert resp.status_code in [400, 422]
    data = resp.json()
    assert data["status"] == "error"
    assert "X-Trace-ID" in resp.headers
