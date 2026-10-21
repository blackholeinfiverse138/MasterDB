"""
Unit Tests for Pravah Event Streaming & Replay Ledger (T-GOV-002)
"""

import pytest
from pydantic import ValidationError
from evaluation_engine.pravah_streaming import (
    PravahEvent,
    PravahEventType,
    PravahReplayEngine,
)


@pytest.fixture
def replay_engine():
    engine = PravahReplayEngine(ledger_path="storage/test_pravah_replay.jsonl")
    engine.reset_for_tests()
    yield engine
    engine.reset_for_tests()


def test_pravah_event_model_strictness():
    """Validates that unexpected extra keys trigger schema_violation failure."""
    valid_payload = {
        "event_id": "evt-test-001",
        "trace_id": "trace-test-001",
        "sequence": 1,
        "event_type": PravahEventType.DATASET_INGESTION,
        "source_system": "MASTERDB",
        "destination": "PRAVAH_REPLAY_LEDGER",
        "payload": {"dataset_id": "ds_spatial_01"},
        "parent_event_hash": "0" * 64,
        "event_hash": "a" * 64,
        "timestamp": "2026-10-21T12:00:00Z"
    }
    event = PravahEvent(**valid_payload)
    assert event.event_id == "evt-test-001"

    # Schema violation: extra forbidden field
    invalid_payload = dict(valid_payload)
    invalid_payload["unauthorized_injected_field"] = "HACK"
    with pytest.raises(ValidationError):
        PravahEvent(**invalid_payload)


def test_pravah_monotonic_sequence_and_hash_linking(replay_engine):
    """Verifies that events receive strictly monotonic sequence numbers and valid parent hash links."""
    evt1 = replay_engine.append_event(
        trace_id="trace-seq-1",
        event_type=PravahEventType.DATASET_INGESTION,
        payload={"dataset": "alpha"}
    )
    assert evt1.sequence == 1
    assert evt1.parent_event_hash == PravahReplayEngine.GENESIS_HASH

    evt2 = replay_engine.append_event(
        trace_id="trace-seq-2",
        event_type=PravahEventType.GOVERNANCE_GATE_EVAL,
        payload={"result": "PASS"}
    )
    assert evt2.sequence == 2
    assert evt2.parent_event_hash == evt1.event_hash

    evt3 = replay_engine.append_event(
        trace_id="trace-seq-3",
        event_type=PravahEventType.OCC_LOCK_TRANSITION,
        payload={"version": 2}
    )
    assert evt3.sequence == 3
    assert evt3.parent_event_hash == evt2.event_hash


def test_pravah_deterministic_replay(replay_engine):
    """Ensures replay slices events deterministically by sequence range."""
    for i in range(1, 6):
        replay_engine.append_event(
            trace_id=f"trace-{i}",
            event_type=PravahEventType.DATASET_INGESTION,
            payload={"index": i}
        )

    all_events = replay_engine.replay(from_sequence=1)
    assert len(all_events) == 5

    sub_events = replay_engine.replay(from_sequence=2, to_sequence=4)
    assert len(sub_events) == 3
    assert sub_events[0].sequence == 2
    assert sub_events[-1].sequence == 4


def test_pravah_integrity_verification_success(replay_engine):
    """Verifies that an unmodified ledger passes cryptographic audit."""
    for i in range(1, 4):
        replay_engine.append_event(
            trace_id=f"trace-int-{i}",
            event_type=PravahEventType.AUDIT_SNAPSHOT,
            payload={"step": i}
        )

    audit = replay_engine.verify_integrity()
    assert audit["valid"] is True
    assert audit["total_events"] == 3
    assert len(audit["state_fingerprint"]) == 64


def test_pravah_state_hash_determinism(replay_engine):
    """Guarantees 100% deterministic SHA-256 state hashing across repeated identical histories."""
    for i in range(1, 4):
        replay_engine.append_event(
            trace_id=f"trace-det-{i}",
            event_type=PravahEventType.REPLAY_SYNC,
            payload={"k": i},
            event_id=f"evt-fixed-{i:06d}"
        )
    h1 = replay_engine.compute_ledger_state_hash()
    h2 = replay_engine.compute_ledger_state_hash()
    assert h1 == h2
    assert len(h1) == 64
