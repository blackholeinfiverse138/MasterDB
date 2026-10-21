"""
Integration Tests - Deterministic Execution Verification (50 Consecutive Runs)
==============================================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
Authority: Parikshak Quality Gate Verification

Strict Quality Gate:
"Deterministic execution: 50 consecutive runs must produce identical SHA-256 state hashes"
"""

import pytest
from fastapi.testclient import TestClient
from evaluation_engine.rule_engine import MasterDBRuleEngine
from task_selector.review_orchestrator import MasterDBReviewOrchestrator
from integrations.local_llm_client import LocalLLMClient


def test_50_consecutive_runs_rule_engine_deterministic_hash():
    """Verify that 50 consecutive runs of rule engine hashing produce identical SHA-256 hashes."""
    engine = MasterDBRuleEngine()
    test_payload = {
        "dataset_id": "DS-FSI-ISFR-2023-FOREST-COVER",
        "category": "geospatial",
        "jurisdiction": "Maharashtra",
        "mdu_schema_ref": "mdu://ontology/environmental/v2.2/forest_cover.schema.json",
        "metrics": {"total_canopy_sqkm": 50798.0, "accuracy_pct": 99.4},
        "governor": "Ansh Gupta",
    }

    hashes = []
    for _ in range(50):
        h = engine.calculate_deterministic_hash(test_payload)
        hashes.append(h)

    assert len(hashes) == 50
    # Strict determinism: all 50 hashes must be identical
    assert len(set(hashes)) == 1
    # Verify valid SHA-256 length
    assert len(hashes[0]) == 64


def test_50_consecutive_runs_review_packet_deterministic_hash():
    """Verify that 50 consecutive runs of review packet orchestration produce identical SHA-256 hashes."""
    orchestrator = MasterDBReviewOrchestrator()
    hashes = []
    for _ in range(50):
        packet = orchestrator.build_review_packet(
            task_id="T-GOV-F01",
            candidate_name="Ansh Gupta",
            dataset_id="DS-FSI-ISFR-2023-FOREST-COVER"
        )
        hashes.append(packet.state_hash)

    assert len(hashes) == 50
    assert len(set(hashes)) == 1
    assert len(hashes[0]) == 64


def test_50_consecutive_runs_local_llm_deterministic_hash():
    """Verify that 50 consecutive offline LLM semantic evaluations produce identical SHA-256 hashes."""
    client = LocalLLMClient(base_url="http://127.0.0.1:99999")
    hashes = []
    for _ in range(50):
        resp = client.verify_dataset_semantic_compliance(
            dataset_name="Thane Creek Mangroves",
            mdu_schema_ref="mdu://ontology/environmental/v2.2/biomass.schema.json",
            declared_purpose="COASTAL_CARBON_ACCOUNTING",
            payload_sample={"biomass_per_hectare": 142.8}
        )
        hashes.append(resp.deterministic_hash)

    assert len(hashes) == 50
    assert len(set(hashes)) == 1
    assert len(hashes[0]) == 64


def test_50_consecutive_runs_api_health_deterministic_state(client: TestClient):
    """Verify that 50 consecutive API health calls return identical SHA-256 deterministic state hashes."""
    hashes = []
    for _ in range(50):
        resp = client.get("/health")
        assert resp.status_code == 200
        hashes.append(resp.json()["deterministic_hash"])

    assert len(hashes) == 50
    assert len(set(hashes)) == 1
    assert len(hashes[0]) == 64
