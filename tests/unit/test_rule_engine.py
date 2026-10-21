"""
Unit Tests - MasterDB Rule Engine & Canonical Gating
===================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from evaluation_engine.rule_engine import (
    MasterDBRuleEngine,
    DatasetClassification,
    SensitivityLevel,
    RuleEvaluationResult,
    EvaluationRubric,
)


def test_rule_engine_initialization():
    engine = MasterDBRuleEngine()
    assert engine.version == "2.0.0"
    assert "CANONICAL" in engine.supported_classifications
    assert "QUARANTINED" in engine.supported_classifications


def test_evaluate_dataset_schema_valid():
    engine = MasterDBRuleEngine()
    dataset = {
        "dataset_id": "DS-TEST-001",
        "owner": "Forest Survey of India",
        "custodian": "Kavy",
        "source": "Official Survey 2023",
        "classification": "CANONICAL",
        "sensitivity": "PUBLIC",
        "access_policy": "POLICY-OPEN",
        "allowed_consumers": ["VANA", "FIN"],
        "intended_use": "Ecosystem analysis",
        "mdu_schema_ref": "mdu://ontology/environmental/v1.0/forest.schema.json",
    }
    passed, results = engine.evaluate_dataset_schema(dataset)
    assert passed is True
    assert len(results) == 3
    assert all(r.passed for r in results)


def test_evaluate_dataset_schema_missing_fields():
    engine = MasterDBRuleEngine()
    dataset = {
        "dataset_id": "DS-INCOMPLETE-001",
        "classification": "CANONICAL",
    }
    passed, results = engine.evaluate_dataset_schema(dataset)
    assert passed is False
    r_schema1 = next(r for r in results if r.rule_id == "R-SCHEMA-01")
    assert r_schema1.passed is False
    assert "owner" in r_schema1.details["missing_fields"]


def test_evaluate_dataset_schema_invalid_taxonomy():
    engine = MasterDBRuleEngine()
    dataset = {
        "dataset_id": "DS-INVALID-TAX-001",
        "owner": "Test Owner",
        "custodian": "Test Custodian",
        "source": "Test Source",
        "classification": "UNREGISTERED_WILDCAT",
        "sensitivity": "PUBLIC",
        "access_policy": "POLICY-OPEN",
        "allowed_consumers": ["VANA"],
        "intended_use": "Testing",
        "mdu_schema_ref": "mdu://ontology/v1.0",
    }
    passed, results = engine.evaluate_dataset_schema(dataset)
    assert passed is False
    r_tax = next(r for r in results if r.rule_id == "R-SCHEMA-02")
    assert r_tax.passed is False


def test_validate_canonical_eligibility_ten_gates():
    engine = MasterDBRuleEngine()
    canonical_valid = {
        "dataset_id": "DS-CANONICAL-001",
        "owner": "MoEFCC",
        "source": {"publisher": "Govt of India", "year": 2023},
        "provenance": "Government Gazette Publication",
        "schema": {"columns": ["id", "canopy_density"]},
        "mdu_schema_ref": "mdu://ontology/forest/v1",
        "classification": "CANONICAL",
        "is_synthetic": False,
        "quality_status": "VALIDATED",
        "allowed_consumers": ["VANA", "FIN"],
        "intended_use": "Ecological canopy verification",
        "fingerprint": "a" * 64,
        "lifecycle_status": "ACTIVE",
        "approval_authority": "Ansh Gupta (Governance Lead)",
    }
    eligible, violations = engine.validate_canonical_eligibility(canonical_valid)
    assert eligible is True
    assert len(violations) == 0


def test_validate_canonical_eligibility_rejects_synthetic():
    engine = MasterDBRuleEngine()
    synthetic_canonical = {
        "dataset_id": "mock_synthetic_dataset",
        "owner": "Tester",
        "source": "Mock Generator",
        "provenance": "Faker Library",
        "schema": {"columns": ["id"]},
        "classification": "CANONICAL",
        "is_synthetic": True,
        "quality_status": "VALIDATED",
        "allowed_consumers": ["TESTER"],
        "intended_use": "Unit test",
        "lifecycle_status": "ACTIVE",
        "approval_authority": "Tester",
    }
    eligible, violations = engine.validate_canonical_eligibility(synthetic_canonical)
    assert eligible is False
    assert any("Synthetic or mock fixtures can NEVER be classified as CANONICAL" in v for v in violations)


def test_evaluate_access_control():
    engine = MasterDBRuleEngine()
    
    # Whitelisted actor for legitimate purpose
    result_allowed = engine.evaluate_access(
        actor="VANA",
        role="consumer",
        dataset_id="DS-FSI-ISFR-2023-FOREST-COVER",
        action="READ",
        purpose="DISTRICT_CANOPY_ANALYSIS"
    )
    assert result_allowed["allowed"] is True
    assert result_allowed["decision"] == "ALLOWED"

    # Anonymous or unknown actor fail-closed
    result_denied_anon = engine.evaluate_access(
        actor="ANONYMOUS",
        role="consumer",
        dataset_id="DS-FSI-ISFR-2023-FOREST-COVER",
        action="READ",
        purpose="DISTRICT_CANOPY_ANALYSIS"
    )
    assert result_denied_anon["allowed"] is False
    assert result_denied_anon["decision"] == "DENIED"

    # Commercial bulk export blocked under purpose limitation
    result_commercial_export = engine.evaluate_access(
        actor="VANA",
        role="consumer",
        dataset_id="DS-FSI-ISFR-2023-FOREST-COVER",
        action="EXPORT",
        purpose="BULK_COMMERCIAL_RESALE"
    )
    assert result_commercial_export["allowed"] is False
    assert "PURPOSE-LIMITATION" in result_commercial_export["rule_code"]


def test_evaluate_dataset_candidate_synthetic_quarantine():
    engine = MasterDBRuleEngine()
    res = engine.evaluate_dataset_candidate(
        dataset_id="mock_fixture_sample_01",
        dataset_name="Synthetic Dummy Sample",
        source_system="generator",
        category="fixture",
        schema_contract={"type": "json"},
    )
    assert res.passed is False
    assert res.rule_id == "R-QUARANTINE-01"
    assert "Quarantined" in res.observation


def test_deterministic_hash_consistency():
    engine = MasterDBRuleEngine()
    payload = {"dataset_id": "DS-TEST", "version": "1.0.0", "items": [1, 2, 3]}
    hash_1 = engine.calculate_deterministic_hash(payload)
    hash_2 = engine.calculate_deterministic_hash(payload)
    assert hash_1 == hash_2
    assert len(hash_1) == 64
