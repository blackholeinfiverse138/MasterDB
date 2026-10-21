# CODE INDEX: ANSH BHIV vNEXT MASTERDB CONVERGENCE & FIN / VANA REAL DATA INTEGRATION (T-GOV-F01)

**Task ID:** `T-GOV-F01`  
**Candidate:** Ansh Gupta  
**Governance Scope:** Full System Completion, Real Data Integration & Schema Violation Remediation  
**Status:** Certified & Verified (75/75 Tests Passing, 94% Coverage)  

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
│   ├── fin_vana_integrator.py            # FIN / VANA real data integration & carbon underwriting
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
    │   ├── test_fin_vana_integrator.py   # Unit tests for FIN / VANA real data & carbon calculations
    │   ├── test_pravah_streaming.py      # Unit tests for Pravah replay engine
    │   ├── test_concurrency_governance.py# Unit tests for OCC & DFA state machine
    │   ├── test_rule_engine.py           # Unit tests for rule engine & eligibility
    │   ├── test_review_orchestrator.py   # Unit tests for review orchestrator & Section 16
    │   ├── test_local_llm_client.py      # Unit tests for local LLM & fallback
    │   └── test_security_middleware.py   # Unit tests for security & replay prevention
    └── integration/
        ├── test_fin_vana_api.py          # Integration tests for FIN / VANA REST endpoints
        ├── test_pravah_and_concurrency_api.py # Integration tests for Pravah & OCC routes
        ├── test_production_api.py        # Integration tests for production API routes
        └── test_deterministic_execution.py# Empirical 50 consecutive run determinism proofs
```

---

## 2. Symbol & Component Reference

### `integrations/fin_vana_integrator.py`
- `class ForestCoverRecord(StrictBase)`: Strict schema for FSI ISFR 2023 Maharashtra district forest cover with ISBN citation.
- `class MangroveBiomassRecord(StrictBase)`: Strict schema for Thane Creek Mangrove plot data with DOI citation.
- `class CarbonUnderwritingRequest(StrictBase)`: Strict inbound contract for FIN carbon underwriting.
- `class CarbonUnderwritingResult(StrictBase)`: Cryptographically verified carbon valuation, NPV, and ESG score.
- `class RealDataRepository`: Authoritative storage of real statutory datasets.
- `class FinVanaIntegrationEngine`:
  - `query_vana_forest_cover(consumer_actor, district, purpose)`: Real ISFR 2023 queries.
  - `query_vana_mangrove_biomass(consumer_actor, zone_query, purpose)`: Real Thane Creek biomass queries.
  - `execute_fin_carbon_underwriting(request)`: IPCC allometry, molecular CO2 conversion ($44/12$), and NPV cash flow.
  - `get_catalog()`: Full catalog of integrated datasets and capabilities.

### `api/production.py`
- **FIN / VANA Endpoints:**
  - `POST /api/v1/integration/vana/forest-cover/query`
  - `POST /api/v1/integration/vana/mangrove-biomass/query`
  - `POST /api/v1/integration/fin/carbon-underwrite`
  - `GET /api/v1/integration/fin-vana/catalog`
- **Governance Endpoints:**
  - `GET /health`, `GET /api/v1/health`
  - `POST /api/v1/governance/evaluate`
  - `POST /api/v1/governance/audit`
  - `POST /api/v1/governance/access-check`
  - `POST /api/v1/convergence/review`
  - `POST /api/v1/semantic/validate`
  - `POST /api/v1/governance/token/verify`
  - `GET /api/v1/governance/status`
  - `POST /api/v1/governance/reset`
- **Pravah & OCC Endpoints:**
  - `POST /api/v1/pravah/stream`
  - `GET /api/v1/pravah/replay`
  - `POST /api/v1/governance/concurrency/transition`
  - `GET /api/v1/governance/concurrency/record/{entity_id}`
- **Parikshak Sync Endpoints:**
  - `POST /api/v1/masterdb/reviews/update`
  - `POST /api/v1/masterdb/candidate/history`
