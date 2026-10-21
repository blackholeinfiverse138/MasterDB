"""
Unit Tests for Concurrency Control & State Machine (T-GOV-002)
"""

import pytest
import threading
from task_selector.state_machine import (
    GovernanceLifecycleState,
    ConcurrencyGovernanceEngine,
    OCCConflictError,
    InvalidStateTransitionError,
)
from evaluation_engine.pravah_streaming import PravahReplayEngine


@pytest.fixture
def concurrency_engine():
    pravah = PravahReplayEngine(ledger_path="storage/test_concurrency_pravah.jsonl")
    engine = ConcurrencyGovernanceEngine(pravah_engine=pravah)
    engine.reset_for_tests()
    yield engine
    engine.reset_for_tests()


def test_concurrency_record_registration(concurrency_engine):
    """Validates initial registration at version 1."""
    rec = concurrency_engine.register_entity(
        entity_id="ds_census_2026",
        initial_state=GovernanceLifecycleState.INIT,
        actor="Steward_Ansh"
    )
    assert rec.entity_id == "ds_census_2026"
    assert rec.state == GovernanceLifecycleState.INIT
    assert rec.version == 1
    assert len(rec.transition_hash) == 64


def test_occ_valid_state_transitions(concurrency_engine):
    """Validates complete DFA advancement path: INIT -> VALIDATING -> AUDITED -> CONVERGED -> CERTIFIED."""
    eid = "ds_geo_highway"
    concurrency_engine.register_entity(entity_id=eid)

    # Transition 1: INIT -> VALIDATING (v1 -> v2)
    r1 = concurrency_engine.transition_state(
        entity_id=eid,
        expected_version=1,
        target_state=GovernanceLifecycleState.VALIDATING,
        actor="Tester",
        trace_id="tr-1"
    )
    assert r1.version == 2
    assert r1.state == GovernanceLifecycleState.VALIDATING

    # Transition 2: VALIDATING -> AUDITED (v2 -> v3)
    r2 = concurrency_engine.transition_state(
        entity_id=eid,
        expected_version=2,
        target_state=GovernanceLifecycleState.AUDITED,
        actor="Auditor",
        trace_id="tr-2"
    )
    assert r2.version == 3
    assert r2.state == GovernanceLifecycleState.AUDITED

    # Transition 3: AUDITED -> CONVERGED (v3 -> v4)
    r3 = concurrency_engine.transition_state(
        entity_id=eid,
        expected_version=3,
        target_state=GovernanceLifecycleState.CONVERGED,
        actor="ConvergenceLead",
        trace_id="tr-3"
    )
    assert r3.version == 4
    assert r3.state == GovernanceLifecycleState.CONVERGED

    # Transition 4: CONVERGED -> CERTIFIED (v4 -> v5)
    r4 = concurrency_engine.transition_state(
        entity_id=eid,
        expected_version=4,
        target_state=GovernanceLifecycleState.CERTIFIED,
        actor="Governor",
        trace_id="tr-4"
    )
    assert r4.version == 5
    assert r4.state == GovernanceLifecycleState.CERTIFIED


def test_occ_conflict_detection_version_mismatch(concurrency_engine):
    """Ensures stale version numbers trigger OCCConflictError (preventing lost updates)."""
    eid = "ds_finance_ledger"
    concurrency_engine.register_entity(entity_id=eid)

    # Advance to v2
    concurrency_engine.transition_state(
        entity_id=eid,
        expected_version=1,
        target_state=GovernanceLifecycleState.VALIDATING,
        actor="OperatorA",
        trace_id="tr-a"
    )

    # Stale operator attempts mutation using old v1
    with pytest.raises(OCCConflictError) as exc_info:
        concurrency_engine.transition_state(
            entity_id=eid,
            expected_version=1,  # STALE
            target_state=GovernanceLifecycleState.AUDITED,
            actor="OperatorB",
            trace_id="tr-b"
        )
    assert "Version mismatch" in str(exc_info.value)
    assert exc_info.value.expected_version == 1
    assert exc_info.value.current_version == 2


def test_occ_illegal_state_transition_rejected(concurrency_engine):
    """Ensures DFA boundaries cannot be bypassed (e.g. INIT directly to CERTIFIED)."""
    eid = "ds_unvetted_shortcut"
    concurrency_engine.register_entity(entity_id=eid)

    # Attempt illegal jump
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        concurrency_engine.transition_state(
            entity_id=eid,
            expected_version=1,
            target_state=GovernanceLifecycleState.CERTIFIED,
            actor="ShortcutAgent",
            trace_id="tr-illegal"
        )
    assert "INVALID_STATE_TRANSITION" in str(exc_info.value)


def test_occ_concurrent_race_condition(concurrency_engine):
    """Verifies that under simultaneous competing threads, exactly one succeeds and others conflict."""
    eid = "ds_race_condition"
    concurrency_engine.register_entity(entity_id=eid)

    successes = []
    conflicts = []

    def worker(worker_id):
        try:
            concurrency_engine.transition_state(
                entity_id=eid,
                expected_version=1,  # All 5 compete for the same initial version
                target_state=GovernanceLifecycleState.VALIDATING,
                actor=f"Worker_{worker_id}",
                trace_id=f"tr-race-{worker_id}"
            )
            successes.append(worker_id)
        except OCCConflictError:
            conflicts.append(worker_id)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly 1 thread must succeed; remaining 4 must fail with OCC conflict
    assert len(successes) == 1
    assert len(conflicts) == 4
    current = concurrency_engine.get_entity_state(eid)
    assert current.version == 2
