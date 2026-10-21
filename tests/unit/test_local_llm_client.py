"""
Unit Tests - Local LLM Integration Client
==========================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from integrations.local_llm_client import LocalLLMClient, LLMVerificationResponse


def test_local_llm_client_initialization():
    client = LocalLLMClient()
    assert client.model_name == "llama3:8b"
    assert client.timeout_seconds == 2.0


def test_offline_fallback_verification_valid():
    client = LocalLLMClient(base_url="http://127.0.0.1:99999")  # Intentionally offline port
    response = client.verify_dataset_semantic_compliance(
        dataset_name="Forest Cover Survey",
        mdu_schema_ref="mdu://ontology/environmental/v1.0/forest.schema.json",
        declared_purpose="DISTRICT_CANOPY_ANALYSIS",
        payload_sample={"density": 85.4}
    )
    assert isinstance(response, LLMVerificationResponse)
    assert response.is_fallback is True
    assert response.verified is True
    assert response.schema_valid is True
    assert "MDU_ALIGNED" in response.compliance_flags
    assert len(response.deterministic_hash) == 64


def test_offline_fallback_flags_invalid_schema():
    client = LocalLLMClient(base_url="http://127.0.0.1:99999")
    response = client.verify_dataset_semantic_compliance(
        dataset_name="Wildcat Dataset",
        mdu_schema_ref="ftp://invalid/schema.json",  # Invalid protocol
        declared_purpose="RESEARCH",
        payload_sample={}
    )
    assert response.is_fallback is True
    assert response.verified is False
    assert response.schema_valid is False
    assert "MDU_SCHEMA_INVALID" in response.compliance_flags


def test_offline_fallback_commercial_restriction():
    client = LocalLLMClient(base_url="http://127.0.0.1:99999")
    response = client.verify_dataset_semantic_compliance(
        dataset_name="Commercial Export Test",
        mdu_schema_ref="mdu://ontology/commercial/v1.0",
        declared_purpose="BULK_COMMERCIAL_RESALE_TO_THIRD_PARTIES",
        payload_sample={}
    )
    assert response.verified is False
    assert "COMMERCIAL_RESTRICTION_TRIGGERED" in response.compliance_flags


def test_extract_governance_entities():
    client = LocalLLMClient()
    text = "The CANONICAL dataset under MASTERDB is governed by MDU schemas and consumed by VANA and BHARAT_MALA."
    entities = client.extract_governance_entities(text)
    assert "CANONICAL" in entities
    assert "MASTERDB" in entities
    assert "MDU" in entities
    assert "VANA" in entities
    assert "BHARAT_MALA" in entities


def test_audit_schema_semantics_red_flag_detection():
    client = LocalLLMClient()
    
    # Violation text
    bad_text = "We allow an unrestricted bypass of the governance boundary for fast debug access."
    res_bad = client.audit_schema_semantics(bad_text)
    assert res_bad.verified is False
    assert "CONSTITUTIONAL_VIOLATION_DETECTED" in res_bad.compliance_flags

    # Clean text
    clean_text = "Standard CANONICAL dataset adhering to MDU ontology and strict constitutional access policy."
    res_clean = client.audit_schema_semantics(clean_text)
    assert res_clean.verified is True
    assert "MDU_ALIGNED" in res_clean.compliance_flags
    assert "CANONICAL_TARGET" in res_clean.compliance_flags
