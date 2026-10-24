"""
Integration Test Suite: MasterDB Biotech & Pharmacovigilance Governance Engine
==============================================================================
Validates the 10 Canonical Eligibility Gates, synthetic data quarantine,
schema strictness, and live source ingestion from MasterDB/sources/.
"""

import pytest
from integrations.biotech_sources_governance import (
    MasterDBBiotechGovernanceEngine,
    PharmacovigilanceEvidenceRecord,
    CompoundAffinityRecord,
    BIOTECH_CANONICAL_PROFILES
)


@pytest.fixture
def engine():
    return MasterDBBiotechGovernanceEngine()


def test_biotech_engine_initialization_and_profiles(engine):
    """Verifies that all canonical profiles are properly registered."""
    profiles = engine.list_registered_profiles()
    assert len(profiles) >= 4
    profile_ids = [p["dataset_id"] for p in profiles]
    assert "DS-FDA-FAERS-ADR-2026" in profile_ids
    assert "DS-CHEMBL-COMPOUND-AFFINITY-01" in profile_ids
    assert "DS-BIOTECH-QC-EVIDENCE-MAP-01" in profile_ids
    assert "DS-BIOTECH-SARA-FORMULATION-001" in profile_ids
    assert "DS-BIOTECH-SYNTHETIC-QUARANTINE-01" in profile_ids


def test_gate_evaluation_valid_pharmacovigilance_record(engine):
    """Tests that a fully compliant real OpenFDA record scores 100/100 across 10 gates."""
    valid_payload = {
        "event_id": "FDA-FAERS-2026-001",
        "drug_name": "Amphotericin B",
        "adverse_event": "Nephrotoxicity",
        "seriousness": "SERIOUS",
        "reporting_date": "2026-03-15",
        "source": "OpenFDA FAERS API",
        "provenance": "US Food and Drug Administration Public Domain Reporting System",
        "owner": "Ansh Gupta",
        "is_synthetic": False
    }
    rubric = engine.evaluate_dataset_eligibility(
        dataset_id="DS-FDA-FAERS-ADR-2026",
        payload=valid_payload,
        actor_role="Auditor"
    )
    assert rubric.overall_pass is True
    assert rubric.score == 100.0
    assert rubric.quarantine_required is False
    assert len(rubric.gate_results) == 10
    assert all(g.passed for g in rubric.gate_results)


def test_gate_evaluation_synthetic_record_quarantined(engine):
    """Tests that synthetic compound data triggers Gate 9 Quarantine and fails overall certification."""
    synthetic_payload = {
        "candidate_id": "TB-SYNTH-999",
        "compound_name": "In-Silico Mock Compound X",
        "target": "Simulated DprE1",
        "mechanism_of_action": "Mock Binding",
        "evidence_stage": "In-Silico Generative",
        "potency": "1.2 nM",
        "source": "Generative Diffusion Model",
        "provenance": "Synthetic Benchmark Generator",
        "owner": "Ansh Gupta",
        "is_synthetic": True  # MUST trigger quarantine
    }
    rubric = engine.evaluate_dataset_eligibility(
        dataset_id="DS-CHEMBL-COMPOUND-AFFINITY-01",
        payload=synthetic_payload,
        actor_role="Auditor"
    )
    assert rubric.overall_pass is False
    assert rubric.quarantine_required is True
    assert rubric.score < 100.0

    # Gate 9 must fail
    g9 = next(g for g in rubric.gate_results if g.gate_id == "GATE-09-SYNTHETIC-QUARANTINE")
    assert g9.passed is False
    assert "QUARANTINED" in g9.details


def test_gate_evaluation_missing_column_schema_violation(engine):
    """Tests that a payload missing a required canonical column fails Gate 2."""
    incomplete_payload = {
        "event_id": "FDA-FAERS-2026-002",
        # "drug_name" is missing!
        "adverse_event": "Rash",
        "seriousness": "MILD",
        "reporting_date": "2026-04-01",
        "source": "OpenFDA FAERS API",
        "provenance": "US FDA FAERS",
        "is_synthetic": False
    }
    rubric = engine.evaluate_dataset_eligibility(
        dataset_id="DS-FDA-FAERS-ADR-2026",
        payload=incomplete_payload,
        actor_role="Auditor"
    )
    assert rubric.overall_pass is False
    g2 = next(g for g in rubric.gate_results if g.gate_id == "GATE-02-SCHEMA")
    assert g2.passed is False
    assert "Missing mandatory canonical column 'drug_name'" in g2.details


def test_gate_evaluation_unauthorized_role_rejected(engine):
    """Tests that an unauthorized consumer actor fails Gate 8."""
    valid_payload = {
        "event_id": "FDA-FAERS-2026-003",
        "drug_name": "Bedaquiline",
        "adverse_event": "Hepatotoxicity",
        "seriousness": "SERIOUS",
        "reporting_date": "2026-05-01",
        "source": "OpenFDA FAERS API",
        "provenance": "US FDA FAERS",
        "owner": "Ansh Gupta",
        "is_synthetic": False
    }
    rubric = engine.evaluate_dataset_eligibility(
        dataset_id="DS-FDA-FAERS-ADR-2026",
        payload=valid_payload,
        actor_role="PublicAnonymous"  # Unauthorized
    )
    assert rubric.overall_pass is False
    g8 = next(g for g in rubric.gate_results if g.gate_id == "GATE-08-ACCESS-CONTROL")
    assert g8.passed is False
    assert "unauthorized" in g8.details.lower()


def test_load_openfda_samples_from_sources(engine):
    """Tests loading real OpenFDA evidence records from sources/bhiv_pharmacovigilance."""
    samples = engine.load_openfda_samples()
    assert len(samples) >= 2
    assert all(isinstance(s, PharmacovigilanceEvidenceRecord) for s in samples)
    assert samples[0].drug_name == "Amphotericin B"
    assert samples[0].is_synthetic is False


def test_load_candidate_compounds_from_csv(engine):
    """Tests loading real TB drug discovery compounds from sources/shamit_drug_discovery/candidate_compounds.csv."""
    compounds = engine.load_candidate_compounds()
    assert len(compounds) > 0
    assert all(isinstance(c, CompoundAffinityRecord) for c in compounds)
    compound_names = [c.compound_name.lower() for c in compounds]
    # Check for known anti-tubercular compounds
    assert any("bedaquiline" in name or "delamanid" in name or "pretomanid" in name or "tbi" in name for name in compound_names)


def test_50_consecutive_runs_deterministic_fingerprint(engine):
    """Verifies that 50 consecutive runs of the gate evaluation yield an identical SHA-256 fingerprint."""
    payload = {
        "event_id": "FDA-FAERS-2026-001",
        "drug_name": "Amphotericin B",
        "adverse_event": "Nephrotoxicity",
        "seriousness": "SERIOUS",
        "reporting_date": "2026-03-15",
        "source": "OpenFDA FAERS API",
        "provenance": "US Food and Drug Administration Public Domain Reporting System",
        "owner": "Ansh Gupta",
        "is_synthetic": False
    }
    first_rubric = engine.evaluate_dataset_eligibility("DS-FDA-FAERS-ADR-2026", payload)
    expected_fp = first_rubric.deterministic_fingerprint

    for _ in range(50):
        rubric = engine.evaluate_dataset_eligibility("DS-FDA-FAERS-ADR-2026", payload)
        assert rubric.deterministic_fingerprint == expected_fp
        assert rubric.score == 100.0
