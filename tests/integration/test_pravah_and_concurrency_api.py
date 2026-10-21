"""
Integration Tests for Pravah Streaming and Concurrency Governance API (T-GOV-002)
"""

import pytest
from fastapi.testclient import TestClient
from api.production import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_state(client):
    headers = {"X-Role": "masterdb_admin"}
    client.post("/api/v1/governance/reset", headers=headers)
    yield
    client.post("/api/v1/governance/reset", headers=headers)


def test_api_pravah_stream_valid_event(client):
    headers = {"X-Role": "governor"}
    payload = {
        "trace_id": "trace-stream-001",
        "event_type": "DATASET_INGESTION",
        "payload": {"dataset_id": "ds_stream_01", "records": 1000},
        "source_system": "MASTERDB",
        "destination": "PRAVAH_REPLAY_LEDGER"
    }
    response = client.post("/api/v1/pravah/stream", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sequence"] == 1
    assert data["trace_id"] == "trace-stream-001"
    assert len(data["event_hash"]) == 64


def test_api_pravah_stream_schema_violation_rejected(client):
    """Enforces strict schema compliance - unexpected field rejected with 422."""
    headers = {"X-Role": "governor"}
    payload = {
        "trace_id": "trace-stream-bad",
        "event_type": "DATASET_INGESTION",
        "payload": {"dataset_id": "ds_stream_01"},
        "unauthorized_field": "TRIGGER_SCHEMA_VIOLATION"
    }
    response = client.post("/api/v1/pravah/stream", json=payload, headers=headers)
    assert response.status_code == 422
    assert "SchemaValidationError" in response.text or "extra_forbidden" in response.text


def test_api_pravah_replay_and_integrity(client):
    headers = {"X-Role": "governor"}

    for i in range(1, 4):
        client.post(
            "/api/v1/pravah/stream",
            json={
                "trace_id": f"trace-rep-{i}",
                "event_type": "GOVERNANCE_GATE_EVAL",
                "payload": {"gate": i, "status": "PASS"}
            },
            headers=headers
        )

    # Replay
    replay_resp = client.post(
        "/api/v1/pravah/replay",
        json={"from_sequence": 1, "to_sequence": 3},
        headers=headers
    )
    assert replay_resp.status_code == 200
    events = replay_resp.json()
    assert len(events) == 3

    # Integrity
    int_resp = client.get("/api/v1/pravah/integrity")
    assert int_resp.status_code == 200
    int_data = int_resp.json()
    assert int_data["valid"] is True
    assert int_data["total_events"] == 3


def test_api_occ_transition_lifecycle_success(client):
    headers = {"X-Role": "governor"}

    # v1 -> v2
    resp1 = client.post(
        "/api/v1/governance/concurrency/transition",
        json={
            "entity_id": "ds_occ_api_01",
            "expected_version": 1,
            "target_state": "VALIDATING",
            "actor": "Governor_Ansh",
            "trace_id": "trace-occ-1",
            "metadata": {"stage": "pre-check"}
        },
        headers=headers
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["version"] == 2
    assert data1["state"] == "VALIDATING"

    # Query state
    get_resp = client.get("/api/v1/governance/concurrency/state/ds_occ_api_01")
    assert get_resp.status_code == 200
    assert get_resp.json()["version"] == 2


def test_api_occ_transition_conflict_returns_409(client):
    """Enforces OCC conflict detection over HTTP API (409 Conflict)."""
    headers = {"X-Role": "governor"}

    # Step 1: Advance to v2
    client.post(
        "/api/v1/governance/concurrency/transition",
        json={
            "entity_id": "ds_conflict_test",
            "expected_version": 1,
            "target_state": "VALIDATING",
            "actor": "WorkerA",
            "trace_id": "trace-a"
        },
        headers=headers
    )

    # Step 2: Competing worker uses stale version 1 -> 409 Conflict
    resp_conflict = client.post(
        "/api/v1/governance/concurrency/transition",
        json={
            "entity_id": "ds_conflict_test",
            "expected_version": 1,  # Stale
            "target_state": "AUDITED",
            "actor": "WorkerB",
            "trace_id": "trace-b"
        },
        headers=headers
    )
    assert resp_conflict.status_code == 409
    assert "OCC_CONFLICT" in resp_conflict.json()["detail"]


def test_api_occ_transition_illegal_dfa_returns_422(client):
    """Enforces DFA state machine boundaries over HTTP API (422 Unprocessable)."""
    headers = {"X-Role": "governor"}

    # Attempt illegal jump from INIT directly to CERTIFIED
    resp_illegal = client.post(
        "/api/v1/governance/concurrency/transition",
        json={
            "entity_id": "ds_illegal_jump",
            "expected_version": 1,
            "target_state": "CERTIFIED",  # Illegal
            "actor": "Intruder",
            "trace_id": "trace-illegal"
        },
        headers=headers
    )
    assert resp_illegal.status_code == 422
    assert "INVALID_STATE_TRANSITION" in resp_illegal.json()["detail"]
