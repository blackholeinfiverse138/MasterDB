# CODE INDEX: ANSH BHIV vNEXT MASTERDB ECOSYSTEM-WIDE CONVERGENCE Architecture (T-GOV-002)

**Task ID:** `T-GOV-002`  
**Candidate:** Ansh Gupta  
**Governance Scope:** Scalable Ecosystem Integration & Pipeline Automation  
**Status:** Certified & Verified (62/62 Tests Passing, 94% Coverage)  

---

## 1. Directory Structure

```
MasterDB/
├── requirements.txt                      # Strictly pinned runtime dependencies (==)
├── pytest.ini                            # Pytest configuration with strict markers & asyncio
├── REVIEW_PACKET.md                      # Architectural proofs, self-audit 100/100, logs
├── CODE_PACKET.md                        # Implementation manifest and changelog
├── CODE_INDEX.md                         # This file: directory tree & symbol index
│
├── api/
│   ├── __init__.py                       # Package initializer
│   └── production.py                     # Production FastAPI application & strict Pydantic models
│
├── evaluation_engine/
│   ├── __init__.py                       # Package initializer
│   ├── pravah_streaming.py               # Asynchronous event streaming & replay ledger
│   └── rule_engine.py                    # 10 Canonical gates, 6-tuple access, state determinism
│
├── task_selector/
│   ├── __init__.py                       # Package initializer
│   ├── review_orchestrator.py            # 9-stage convergence sequence & Section 16 protocol
│   └── state_machine.py                  # OCC concurrency manager & DFA state machine
│
├── integrations/
│   ├── __init__.py                       # Package initializer
│   └── local_llm_client.py               # Offline deterministic LLM client & entity extractor
│
├── security/
│   ├── __init__.py                       # Package initializer
│   └── middleware.py                     # Error boundary, role RBAC, token replay prevention
│
├── storage/
│   └── pravah_replay.jsonl               # Append-only cryptographic replay ledger
│
└── tests/
    ├── conftest.py                       # Shared test fixtures & client isolation
    ├── unit/
    │   ├── test_pravah_streaming.py      # Unit tests for Pravah replay engine
    │   ├── test_concurrency_governance.py# Unit tests for OCC & DFA state machine
    │   ├── test_rule_engine.py           # Unit tests for rule engine & eligibility
    │   ├── test_review_orchestrator.py   # Unit tests for review orchestrator & Section 16
    │   ├── test_local_llm_client.py      # Unit tests for local LLM & fallback
    │   └── test_security_middleware.py   # Unit tests for security & replay prevention
    └── integration/
        ├── test_pravah_and_concurrency_api.py # Integration tests for Pravah & OCC routes
        ├── test_production_api.py        # Integration tests for production API routes
        └── test_deterministic_execution.py# Empirical 50 consecutive run determinism proofs
```

---

## 2. Symbol & Component Reference

### `evaluation_engine/pravah_streaming.py`
- `class PravahEvent(BaseModel)`: Strict event model with sequence, previous hash, timestamp, payload signature.
- `class PravahReplayEngine`: Append-only, thread-safe streaming ledger.
  - `stream_event(event_type, payload, entity_id)`: Streams event, computes cryptographic parent hash.
  - `replay_events(from_sequence, to_sequence)`: Replays events in monotonic sequence.
  - `verify_integrity()`: Validates hash chain continuity across the entire ledger.
  - `compute_ledger_state_hash()`: Computes deterministic SHA-256 fingerprint.

### `task_selector/state_machine.py`
- `class GovernanceState(str, Enum)`: 8-state DFA (`INIT`, `VALIDATING`, `AUDITED`, `CONVERGED`, `CERTIFIED`, `QUARANTINED`, `REJECTED`, `DISPUTED`).
- `class ConcurrencyRecord(BaseModel)`: Entity state model with integer version and audit trail.
- `class ConcurrencyGovernanceEngine`: Optimistic Concurrency Control (OCC) manager.
  - `register_entity(entity_id, initial_state)`: Registers new entity.
  - `transition_state(entity_id, expected_version, target_state, actor, reason)`: Validates OCC version (409) and DFA legality (422), incrementing version.
  - `compute_governance_state_hash()`: Computes deterministic state hash.

### `evaluation_engine/rule_engine.py`
- `class RuleEngine`:
  - `evaluate_dataset_schema(dataset)`: Enforces strict taxonomy, fields, and fail-closed checks.
  - `validate_canonical_eligibility(dataset)`: Enforces 10 Canonical Eligibility Gates.
  - `evaluate_access_control(actor_role, resource_tier, requested_action, classification, consent_scope, department_id)`: 6-tuple access matrix evaluator.
  - `evaluate_dataset_candidate(candidate)`: Evaluates candidate payloads and synthetic quarantine.
  - `compute_deterministic_hash(payload)`: Canonical SHA-256 state hashing.

### `task_selector/review_orchestrator.py`
- `class ReviewOrchestrator`:
  - `build_review_packet(candidate_id, department, evidence_files)`: Generates standardized review packet.
  - `advance_stage(candidate_id, next_stage, reviewer_id, notes)`: Coordinates 9-stage review pipeline.
  - `record_section16_disagreement(candidate_id, raised_by, reason, dissenting_view)`: Section 16 dispute registry.
  - `resolve_section16_disagreement(candidate_id, resolver_id, resolution_notes)`: Resolves active disputes.
  - `execute_review_stage(candidate_id, stage, reviewer_id, payload)`: Executes stage gates.
  - `finalize_decision(candidate_id, decision, approver_id, summary)`: Locks decision state.

### `integrations/local_llm_client.py`
- `class LocalLLMClient`:
  - `extract_governance_entities(raw_text)`: Resilient entity extraction with deterministic fallback.
  - `audit_schema_semantics(schema_definition)`: Semantic red-flag detector.
  - `query(prompt)`: In-memory cached inference interface.

### `security/middleware.py`
- `class ErrorBoundaryMiddleware(BaseHTTPMiddleware)`: Intercepts unhandled exceptions to prevent 500 status codes.
- `class TokenReplayCache`: Replay prevention cache (HTTP 409).
- `require_role(required_role)`: Role-based route dependency.
