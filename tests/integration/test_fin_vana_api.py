"""
Integration Tests - FIN / VANA Real Data Production API
========================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from fastapi.testclient import TestClient


def test_query_vana_forest_cover_api(client: TestClient):
    headers = {"X-Role": "consumer"}
    payload = {
        "consumer_actor": "VANA",
        "district": "Ratnagiri",
        "purpose": "DISTRICT_CANOPY_ANALYSIS"
    }
    resp = client.post("/api/v1/integration/vana/forest-cover/query", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["records_count"] == 1
    assert data["records"][0]["district"] == "Ratnagiri"
    assert data["records"][0]["total_forest_cover_km2"] == 4137.80
    assert len(data["data_sha256"]) == 64


def test_query_vana_forest_cover_unknown_district_404(client: TestClient):
    headers = {"X-Role": "consumer"}
    payload = {
        "consumer_actor": "VANA",
        "district": "UnknownHimalayanDistrict",
        "purpose": "DISTRICT_CANOPY_ANALYSIS"
    }
    resp = client.post("/api/v1/integration/vana/forest-cover/query", json=payload, headers=headers)
    assert resp.status_code == 404
    assert "No forest cover records found" in resp.json()["detail"]


def test_query_vana_mangrove_biomass_api(client: TestClient):
    headers = {"X-Role": "consumer"}
    payload = {
        "consumer_actor": "VANA",
        "zone_query": "Bhandup",
        "purpose": "BLUE_CARBON_QUANTIFICATION"
    }
    resp = client.post("/api/v1/integration/vana/mangrove-biomass/query", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["records_count"] == 1
    assert "Bhandup" in data["records"][0]["sanctuary_zone"]
    assert data["records"][0]["measured_agb_mg_per_ha"] == 62.45


def test_execute_fin_carbon_underwrite_api(client: TestClient):
    headers = {"X-Role": "consumer"}
    payload = {
        "project_id": "PROJ-FIN-ESG-PUNE-01",
        "underwriter_actor": "FIN",
        "target_dataset_id": "DS-FSI-ISFR-2023-FOREST-COVER",
        "target_district_or_plot": "Pune",
        "underwriting_purpose": "ESG_CARBON_UNDERWRITING",
        "carbon_price_usd_per_ton": 28.5,
        "project_lifespan_years": 20,
        "discount_rate_pct": 6.5,
    }
    resp = client.post("/api/v1/integration/fin/carbon-underwrite", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "PROJ-FIN-ESG-PUNE-01"
    assert data["target_area"] == "Pune"
    assert data["carbon_stock_t_c"] > 0
    assert data["net_present_value_usd"] > 0
    assert len(data["evidence_hash"]) == 64


def test_fin_underwrite_strict_schema_rejection(client: TestClient):
    headers = {"X-Role": "consumer"}
    # Passing unexpected extra field violates strict Pydantic model (extra="forbid")
    payload = {
        "project_id": "PROJ-FIN-FAIL-01",
        "underwriter_actor": "FIN",
        "target_dataset_id": "DS-FSI-ISFR-2023-FOREST-COVER",
        "target_district_or_plot": "Pune",
        "underwriting_purpose": "ESG_CARBON_UNDERWRITING",
        "unexpected_extra_field": "disallowed_key_schema_violation",
    }
    resp = client.post("/api/v1/integration/fin/carbon-underwrite", json=payload, headers=headers)
    assert resp.status_code == 422
    data = resp.json()
    assert data["status"] == "error"
    assert data["error_type"] == "SchemaValidationError"


def test_get_fin_vana_catalog_api(client: TestClient):
    resp = client.get("/api/v1/integration/fin-vana/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert "FIN" in data["integrated_systems"]
    assert "VANA" in data["integrated_systems"]
    assert data["total_forest_records"] == 5
    assert data["total_mangrove_records"] == 5


def test_50_consecutive_runs_fin_carbon_underwriting_determinism(client: TestClient):
    """50 consecutive runs of FIN underwriting must yield identical evidence hashes."""
    headers = {"X-Role": "consumer"}
    payload = {
        "project_id": "PROJ-DETERMINISM-50",
        "underwriter_actor": "FIN",
        "target_dataset_id": "DS-THANECREEK-2023-BIOMASS",
        "target_district_or_plot": "Airoli",
        "underwriting_purpose": "BLUE_CARBON_QUANTIFICATION",
        "carbon_price_usd_per_ton": 30.0,
        "project_lifespan_years": 20,
        "discount_rate_pct": 6.0,
    }

    hashes = []
    for _ in range(50):
        resp = client.post("/api/v1/integration/fin/carbon-underwrite", json=payload, headers=headers)
        assert resp.status_code == 200
        hashes.append(resp.json()["evidence_hash"])

    assert len(hashes) == 50
    assert len(set(hashes)) == 1
    assert len(hashes[0]) == 64
