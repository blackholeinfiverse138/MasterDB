# CODE INDEX: ANSH BHIV vNEXT MASTERDB ECOSYSTEM-WIDE CONVERGENCE Architecture (T-GOV-F01)

**Task ID:** `T-GOV-F01`  
**Candidate:** Ansh Gupta  
**Governance Scope:** MasterDB Convergence Architecture & Schema Violation Remediation  
**Status:** Certified & Verified  

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
│   └── rule_engine.py                    # 10 Canonical gates, 6-tuple access, state determinism
│
├── task_selector/
│   ├── __init__.py                       # Package initializer
│   └── review_orchestrator.py            # 9-stage convergence sequence & Section 16 protocol
│
├── integrations/
│   ├── __init__.py                       # Package initializer
│   └── local_llm_client.py               # Offline deterministic LLM client & entity extractor
│
├── security/
│   ├── __init__.py                       # Package initializer
│   └── middleware.py                     # Error boundary, role RBAC, token replay prevention
│
└── tests/
    ├── __init__.py                       # Package initializer
    ├── conftest.py                       # Global test fixtures, client, and environment cleanups
    ├── unit/
    │   ├── __init__.py                   # Package initializer
    │   ├── test_rule_engine.py           # Unit tests for rule engine & 10 gates
    │   ├── test_review_orchestrator.py   # Unit tests for orchestrator & Section 16 protocol
    │   ├── test_security_middleware.py   # Unit tests for RBAC, replay prevention, error boundary
    │   └── test_local_llm_client.py      # Unit tests for offline LLM heuristics & entities
    └── integration/
        ├── __init__.py                   # Package initializer
        ├── test_production_api.py        # Integration tests for all REST endpoints & error handling
        └── test_deterministic_execution.py # 50 consecutive runs determinism proof
```

---

## 2. Component & Symbol Index

### 2.1 `api/production.py`
- **Application:** `app: FastAPI`
- **Pydantic Schema Models (`extra='forbid'`):**
  - `HealthResponse`: System operational status and SHA-256 fingerprint.
  - `DatasetEvaluationRequest`: Inbound dataset candidate ingestion schema.
  - `DatasetAuditRequest`: 10-gate canonical audit parameters.
  - `AccessCheckRequest`: 6-tuple constitutional access verification request.
  - `ConvergenceReviewRequest`: 9-stage convergence review request.
  - `SemanticValidationRequest`: Schema and governance profile semantic validation.
  - `TokenVerificationRequest`: Single-use token verification and replay prevention.
  - `StatusResponse`: MasterDB engine metrics and state hash.
- **REST Endpoints:**
  - `GET /health`, `GET /api/v1/health`
  - `POST /api/v1/governance/evaluate`
  - `POST /api/v1/governance/audit`
  - `POST /api/v1/governance/access-check`
  - `POST /api/v1/convergence/review`
  - `POST /api/v1/semantic/validate`
  - `POST /api/v1/governance/token/verify`
  - `GET /api/v1/governance/status`
  - `POST /api/v1/governance/reset`

### 2.2 `evaluation_engine/rule_engine.py`
- **Classes & Enums:**
  - `DatasetClassification`: `CANONICAL`, `SOURCE`, `DERIVED`, `EXPERIMENTAL`, `FIXTURE`, `QUARANTINED`, etc.
  - `SensitivityLevel`: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, `CRITICAL_INFRASTRUCTURE`.
  - `RuleEvaluationResult`: Atomic rule score and observation model.
  - `EvaluationRubric`: Composite Parikshak evaluation rubric.
  - `MasterDBRuleEngine`: Deterministic governance engine implementing:
    - `evaluate_dataset_schema(dataset)`: Strict mandatory fields and taxonomy checks.
    - `validate_canonical_eligibility(dataset)`: 10 Canonical Eligibility Gates enforcement.
    - `evaluate_access(actor, role, dataset_id, action, purpose, ...)`: 6-tuple access evaluation.
    - `evaluate_access_request(...)`: High-level route adapter.
    - `evaluate_dataset_candidate(...)`: Ingestion candidate evaluation with synthetic quarantine.
    - `evaluate_canonical_gates(...)`: 10 individual gate audits.
    - `calculate_deterministic_hash(payload)`: Guaranteed deterministic SHA-256 state hashing.
    - `compute_state_hash()`: Engine state hash computation.

### 2.3 `task_selector/review_orchestrator.py`
- **Classes & Enums:**
  - `ReviewStage`: 9-stage convergence review lifecycle enum.
  - `DecisionState`: `APPROVED`, `APPROVED_WITH_FIXES`, `REVISION_REQUIRED`, `REJECTED`.
  - `Section16Disagreement`: Formal protocol model for recording independent audit disagreements.
  - `ReviewPacketContract`: Parikshak review packet contract with SHA-256 state hash.
  - `MasterDBReviewOrchestrator`: Orchestration engine implementing:
    - `register_disagreement(disagreement)`: Section 16 independent audit logging.
    - `resolve_disagreement(index, notes)`: Audit resolution mechanism.
    - `execute_review_stage(...)`: Executes stage review, enforcing Section 16 signoff.
    - `build_review_packet(...)`: Assembles canonical review packet.
    - `advance_stage(current_stage)`: Progresses through convergence lifecycle.

### 2.4 `integrations/local_llm_client.py`
- **Classes:**
  - `LLMVerificationResponse`: Semantic audit output with extracted entities and compliance flags.
  - `LocalLLMClient`: Resilient client implementing:
    - `verify_dataset_semantic_compliance(...)`: Remote LLM call with offline fallback.
    - `audit_schema_semantics(...)`: Heuristic schema validation and constitutional red-flag detection.
    - `_deterministic_fallback_verification(...)`: Guaranteed deterministic offline fallback.
    - `extract_governance_entities(text)`: Deterministic governance entity extractor.

### 2.5 `security/middleware.py`
- **Classes & Enums:**
  - `UserRole`: `governor`, `auditor`, `steward`, `consumer`, `masterdb_admin`, `ansh_gov_lead`, `parikshak_evaluator`.
  - `SecurityError`, `TokenReplayError`, `RoleUnauthorizedError`.
  - `ErrorBoundaryMiddleware`: ASGI middleware trapping all unhandled exceptions (zero unhandled 500s).
- **Functions:**
  - `register_used_token(token, metadata)`: Replay prevention token consumer.
  - `is_token_spent(token)`: Query spent status.
  - `reset_spent_tokens()`: Test harness cleanup.
  - `require_role(allowed_roles)`: FastAPI role-based access dependency.
