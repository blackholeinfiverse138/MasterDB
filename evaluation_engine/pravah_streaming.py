"""
Pravah Event-Driven Streaming & Replay Ledger Engine - MasterDB vNext (T-GOV-002)
================================================================================
Task ID: T-GOV-002
Candidate: Ansh Gupta (Product Governance: BHIV)
Authority: MasterDB Ecosystem Interoperability & Pipeline Automation

Implements asynchronous event streaming, cryptographic hash-chained replay ledgers,
and strict sequence validation for ecosystem pipeline automation.
"""

from __future__ import annotations

import os
import json
import hashlib
import time
import threading
import unicodedata
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


def canonical_json(data: Any) -> str:
    """Deterministically serializes dictionaries with sorted keys, no spaces, and NFC UTF-8 normalization."""
    raw_str = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return unicodedata.normalize('NFC', raw_str)


class PravahEventType(str, Enum):
    DATASET_INGESTION = "DATASET_INGESTION"
    GOVERNANCE_GATE_EVAL = "GOVERNANCE_GATE_EVAL"
    OCC_LOCK_TRANSITION = "OCC_LOCK_TRANSITION"
    REPLAY_SYNC = "REPLAY_SYNC"
    AUDIT_SNAPSHOT = "AUDIT_SNAPSHOT"
    CIRCUIT_BREAKER_TRIP = "CIRCUIT_BREAKER_TRIP"


class PravahEvent(BaseModel):
    """Cryptographically verified event record for Pravah event streaming."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    event_id: str = Field(..., min_length=4, max_length=128, description="Unique event UUID/ID")
    trace_id: str = Field(..., min_length=4, max_length=128, description="Distributed trace ID")
    sequence: int = Field(..., ge=1, description="Strictly monotonic sequence counter")
    event_type: PravahEventType = Field(..., description="Canonical Pravah event type")
    source_system: str = Field(..., min_length=2, max_length=64, description="Originating system")
    destination: str = Field(..., min_length=2, max_length=64, description="Target subsystem")
    payload: Dict[str, Any] = Field(..., description="Canonical event payload data")
    parent_event_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 of previous event in chain")
    event_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 cryptographic chain hash")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")

    @classmethod
    def compute_hash(
        cls,
        event_id: str,
        trace_id: str,
        sequence: int,
        event_type: str,
        source_system: str,
        destination: str,
        payload: Dict[str, Any],
        parent_event_hash: str,
        timestamp: str
    ) -> str:
        payload_str = canonical_json(payload)
        hash_input = (
            f"{event_id}|{trace_id}|{sequence}|{event_type}|"
            f"{source_system}|{destination}|{payload_str}|{parent_event_hash}|{timestamp}"
        )
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


class PravahReplayEngine:
    """
    Authoritative event stream processor and replay ledger for MasterDB and Pravah.
    Maintains append-only durability, thread-safe sequence increments, and zero-drift replay.
    """

    GENESIS_HASH: str = "0" * 64

    def __init__(self, ledger_path: str = "storage/pravah_replay.jsonl"):
        self.ledger_path = ledger_path
        self.lock = threading.RLock()
        self._in_memory_events: List[PravahEvent] = []
        os.makedirs(os.path.dirname(self.ledger_path) if os.path.dirname(self.ledger_path) else "storage", exist_ok=True)
        self._load_existing_ledger()

    def _load_existing_ledger(self) -> None:
        with self.lock:
            self._in_memory_events.clear()
            if os.path.exists(self.ledger_path):
                try:
                    with open(self.ledger_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                data = json.loads(line)
                                self._in_memory_events.append(PravahEvent(**data))
                except Exception:
                    pass

    @property
    def current_sequence(self) -> int:
        with self.lock:
            return len(self._in_memory_events)

    @property
    def last_event_hash(self) -> str:
        with self.lock:
            if not self._in_memory_events:
                return self.GENESIS_HASH
            return self._in_memory_events[-1].event_hash

    def append_event(
        self,
        trace_id: str,
        event_type: PravahEventType,
        payload: Dict[str, Any],
        source_system: str = "MASTERDB",
        destination: str = "PRAVAH_REPLAY_LEDGER",
        event_id: Optional[str] = None
    ) -> PravahEvent:
        """
        Appends an event to the ledger with strict monotonic sequencing and hash linking.
        Thread-safe under high concurrency.
        """
        with self.lock:
            seq = len(self._in_memory_events) + 1
            evt_id = event_id or f"evt-pravah-{seq:06d}-{hashlib.md5(f'{trace_id}{time.time()}'.encode()).hexdigest()[:8]}"
            parent_hash = self._in_memory_events[-1].event_hash if self._in_memory_events else self.GENESIS_HASH
            ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            event_hash = PravahEvent.compute_hash(
                event_id=evt_id,
                trace_id=trace_id,
                sequence=seq,
                event_type=event_type.value if hasattr(event_type, 'value') else str(event_type),
                source_system=source_system,
                destination=destination,
                payload=payload,
                parent_event_hash=parent_hash,
                timestamp=ts
            )

            event = PravahEvent(
                event_id=evt_id,
                trace_id=trace_id,
                sequence=seq,
                event_type=event_type,
                source_system=source_system,
                destination=destination,
                payload=payload,
                parent_event_hash=parent_hash,
                event_hash=event_hash,
                timestamp=ts
            )

            # Persist to disk atomically
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.model_dump(), sort_keys=True) + "\n")

            self._in_memory_events.append(event)
            return event

    def replay(self, from_sequence: int = 1, to_sequence: Optional[int] = None) -> List[PravahEvent]:
        """
        Deterministically replays events from `from_sequence` up to `to_sequence`.
        """
        with self.lock:
            start_idx = max(0, from_sequence - 1)
            end_idx = to_sequence if to_sequence is not None else len(self._in_memory_events)
            return list(self._in_memory_events[start_idx:end_idx])

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Validates cryptographic hash continuity and strictly monotonic sequencing.
        """
        with self.lock:
            last_hash = self.GENESIS_HASH
            expected_seq = 1
            for evt in self._in_memory_events:
                if evt.sequence != expected_seq:
                    return {
                        "valid": False,
                        "error": f"SEQUENCE_GAP: Expected {expected_seq}, found {evt.sequence}",
                        "failing_sequence": evt.sequence
                    }
                if evt.parent_event_hash != last_hash:
                    return {
                        "valid": False,
                        "error": f"HASH_DISCONTINUITY: Event {evt.sequence} parent hash mismatch",
                        "failing_sequence": evt.sequence
                    }
                recomputed = PravahEvent.compute_hash(
                    event_id=evt.event_id,
                    trace_id=evt.trace_id,
                    sequence=evt.sequence,
                    event_type=evt.event_type.value if hasattr(evt.event_type, 'value') else str(evt.event_type),
                    source_system=evt.source_system,
                    destination=evt.destination,
                    payload=evt.payload,
                    parent_event_hash=evt.parent_event_hash,
                    timestamp=evt.timestamp
                )
                if recomputed != evt.event_hash:
                    return {
                        "valid": False,
                        "error": f"CORRUPTED_EVENT_HASH: Recomputed hash does not match stored hash for seq {evt.sequence}",
                        "failing_sequence": evt.sequence
                    }
                last_hash = evt.event_hash
                expected_seq += 1

            return {
                "valid": True,
                "total_events": len(self._in_memory_events),
                "head_sequence": len(self._in_memory_events),
                "head_hash": last_hash,
                "state_fingerprint": self.compute_ledger_state_hash()
            }

    def compute_ledger_state_hash(self) -> str:
        """Computes deterministic SHA-256 state hash of entire replay ledger."""
        with self.lock:
            if not self._in_memory_events:
                return hashlib.sha256(b"EMPTY_PRAVAH_LEDGER").hexdigest()
            serialized = canonical_json([e.model_dump() for e in self._in_memory_events])
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def reset_for_tests(self) -> None:
        """Cleans up ledger state for test isolation."""
        with self.lock:
            self._in_memory_events.clear()
            if os.path.exists(self.ledger_path):
                try:
                    os.remove(self.ledger_path)
                except Exception:
                    pass
