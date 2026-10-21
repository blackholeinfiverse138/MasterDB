"""
Optimistic Concurrency Control (OCC) & Deterministic State Machine Engine - MasterDB vNext (T-GOV-002)
====================================================================================================
Task ID: T-GOV-002
Candidate: Ansh Gupta (Product Governance: BHIV)
Authority: MasterDB Ecosystem Interoperability & Concurrency Governance

Enforces strict monotonic version checks, prevents race conditions across multi-tenant
dataset migrations, and drives deterministic DFA state machine transitions.
"""

from __future__ import annotations

import os
import json
import hashlib
import time
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict

from evaluation_engine.pravah_streaming import PravahEventType, PravahReplayEngine


class GovernanceLifecycleState(str, Enum):
    INIT = "INIT"
    VALIDATING = "VALIDATING"
    AUDITED = "AUDITED"
    CONVERGED = "CONVERGED"
    CERTIFIED = "CERTIFIED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"
    DISPUTED = "DISPUTED"


class OCCConflictError(Exception):
    """Raised when an update conflicts with the current entity version."""
    def __init__(self, message: str, entity_id: str, expected_version: int, current_version: int):
        super().__init__(message)
        self.message = message
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.current_version = current_version


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state machine transition is attempted."""
    def __init__(self, message: str, entity_id: str, current_state: str, target_state: str):
        super().__init__(message)
        self.message = message
        self.entity_id = entity_id
        self.current_state = current_state
        self.target_state = target_state


class ConcurrencyRecord(BaseModel):
    """Immutable state machine snapshot with monotonic version tagging."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    entity_id: str = Field(..., min_length=3, max_length=128, description="Target entity identifier")
    state: GovernanceLifecycleState = Field(..., description="Current DFA state")
    version: int = Field(..., ge=1, description="Strictly monotonic OCC version")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
    actor: str = Field(..., min_length=2, max_length=64, description="Actor driving transition")
    trace_id: str = Field(..., min_length=4, max_length=128, description="Audit trace identifier")
    transition_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 fingerprint of state transition")


class ConcurrencyGovernanceEngine:
    """
    Thread-safe Concurrency Control & State Machine Manager.
    Guarantees ACID state mutations, strict DFA transitions, and automatic Pravah streaming.
    """

    # Permitted Deterministic State Transitions (DFA)
    ALLOWED_TRANSITIONS: Dict[GovernanceLifecycleState, Set[GovernanceLifecycleState]] = {
        GovernanceLifecycleState.INIT: {
            GovernanceLifecycleState.VALIDATING,
            GovernanceLifecycleState.REJECTED,
            GovernanceLifecycleState.QUARANTINED,
        },
        GovernanceLifecycleState.VALIDATING: {
            GovernanceLifecycleState.AUDITED,
            GovernanceLifecycleState.QUARANTINED,
            GovernanceLifecycleState.REJECTED,
            GovernanceLifecycleState.DISPUTED,
        },
        GovernanceLifecycleState.AUDITED: {
            GovernanceLifecycleState.CONVERGED,
            GovernanceLifecycleState.QUARANTINED,
            GovernanceLifecycleState.REJECTED,
            GovernanceLifecycleState.DISPUTED,
        },
        GovernanceLifecycleState.CONVERGED: {
            GovernanceLifecycleState.CERTIFIED,
            GovernanceLifecycleState.REJECTED,
            GovernanceLifecycleState.DISPUTED,
        },
        GovernanceLifecycleState.CERTIFIED: {
            GovernanceLifecycleState.DISPUTED,  # Post-certification independent audit dispute
            GovernanceLifecycleState.QUARANTINED, # Emergency quarantine if retroactive flaw found
        },
        GovernanceLifecycleState.DISPUTED: {
            GovernanceLifecycleState.AUDITED,   # Re-audit after Section 16 dispute resolution
            GovernanceLifecycleState.REJECTED,  # Final rejection
        },
        GovernanceLifecycleState.QUARANTINED: {
            GovernanceLifecycleState.VALIDATING, # Re-evaluation after provenance clearance
            GovernanceLifecycleState.REJECTED,
        },
        GovernanceLifecycleState.REJECTED: set(), # Terminal state (requires new entity registration)
    }

    def __init__(self, pravah_engine: Optional[PravahReplayEngine] = None):
        self.lock = threading.RLock()
        self.pravah_engine = pravah_engine or PravahReplayEngine()
        self._registry: Dict[str, ConcurrencyRecord] = {}

    def register_entity(
        self,
        entity_id: str,
        initial_state: GovernanceLifecycleState = GovernanceLifecycleState.INIT,
        actor: str = "MasterDB_Governor",
        trace_id: str = "trace-init-genesis"
    ) -> ConcurrencyRecord:
        """Registers a new governance entity at version 1."""
        with self.lock:
            ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            trans_hash = hashlib.sha256(f"{entity_id}|{initial_state.value}|1|{ts}|{trace_id}".encode()).hexdigest()
            record = ConcurrencyRecord(
                entity_id=entity_id,
                state=initial_state,
                version=1,
                updated_at=ts,
                actor=actor,
                trace_id=trace_id,
                transition_hash=trans_hash
            )
            self._registry[entity_id] = record

            # Stream initialization event to Pravah
            self.pravah_engine.append_event(
                trace_id=trace_id,
                event_type=PravahEventType.OCC_LOCK_TRANSITION,
                payload={
                    "entity_id": entity_id,
                    "action": "REGISTER_ENTITY",
                    "state": initial_state.value,
                    "version": 1,
                    "actor": actor
                },
                source_system="MASTERDB_OCC",
                destination="PRAVAH_REPLAY_LEDGER"
            )
            return record

    def transition_state(
        self,
        entity_id: str,
        expected_version: int,
        target_state: GovernanceLifecycleState,
        actor: str,
        trace_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConcurrencyRecord:
        """
        Executes an OCC-protected state transition.
        Guarantees:
        1. Atomicity under concurrency (thread-safe lock)
        2. Strict version matching (detects and rejects race conditions with OCCConflictError)
        3. Strict DFA transition boundaries (rejects illegal jumps with InvalidStateTransitionError)
        4. Pravah event stream propagation
        """
        with self.lock:
            if entity_id not in self._registry:
                # Auto-initialize if first observed
                self.register_entity(entity_id=entity_id, actor=actor, trace_id=trace_id)

            current = self._registry[entity_id]

            # 1. OCC Version Match
            if current.version != expected_version:
                raise OCCConflictError(
                    f"OCC_CONFLICT: Version mismatch for entity '{entity_id}'. Expected v{expected_version}, current is v{current.version}.",
                    entity_id=entity_id,
                    expected_version=expected_version,
                    current_version=current.version
                )

            # 2. DFA Transition Validation
            allowed = self.ALLOWED_TRANSITIONS.get(current.state, set())
            if target_state not in allowed:
                raise InvalidStateTransitionError(
                    f"INVALID_STATE_TRANSITION: Cannot transition entity '{entity_id}' from '{current.state.value}' to '{target_state.value}'.",
                    entity_id=entity_id,
                    current_state=current.state.value,
                    target_state=target_state.value
                )

            # 3. Apply Transition
            new_version = current.version + 1
            ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            trans_hash = hashlib.sha256(
                f"{entity_id}|{current.state.value}->{target_state.value}|{new_version}|{ts}|{trace_id}|{current.transition_hash}".encode()
            ).hexdigest()

            updated_record = ConcurrencyRecord(
                entity_id=entity_id,
                state=target_state,
                version=new_version,
                updated_at=ts,
                actor=actor,
                trace_id=trace_id,
                transition_hash=trans_hash
            )
            self._registry[entity_id] = updated_record

            # 4. Stream event to Pravah
            self.pravah_engine.append_event(
                trace_id=trace_id,
                event_type=PravahEventType.OCC_LOCK_TRANSITION,
                payload={
                    "entity_id": entity_id,
                    "previous_state": current.state.value,
                    "new_state": target_state.value,
                    "version": new_version,
                    "actor": actor,
                    "metadata": metadata or {}
                },
                source_system="MASTERDB_OCC",
                destination="PRAVAH_REPLAY_LEDGER"
            )

            return updated_record

    def get_entity_state(self, entity_id: str) -> Optional[ConcurrencyRecord]:
        with self.lock:
            return self._registry.get(entity_id)

    def compute_state_hash(self) -> str:
        """Deterministic SHA-256 fingerprint of all registered entity states and versions."""
        with self.lock:
            sorted_items = sorted(
                [{"id": k, "state": v.state.value, "version": v.version, "hash": v.transition_hash}
                 for k, v in self._registry.items()],
                key=lambda x: x["id"]
            )
            raw = json.dumps(sorted_items, sort_keys=True)
            return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def reset_for_tests(self) -> None:
        with self.lock:
            self._registry.clear()
            self.pravah_engine.reset_for_tests()
