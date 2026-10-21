"""
Unit Tests - FIN / VANA Real Data Integration Engine
=====================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from integrations.fin_vana_integrator import (
    RealDataRepository,
    FinVanaIntegrationEngine,
    CarbonUnderwritingRequest,
    CarbonUnderwritingResult,
    ForestCoverRecord,
    MangroveBiomassRecord,
)


def test_repository_initialization():
    repo = RealDataRepository()
    forest_records = repo.get_forest_cover()
    mangrove_records = repo.get_mangrove_biomass()

    assert len(forest_records) == 5
    assert len(mangrove_records) == 5

    # Check real citations
    assert any("ISBN 978-81-950073-9-4" in r.citation for r in forest_records)
    assert any("10.1016/j.ecolind.2023.109876" in r.citation for r in mangrove_records)


def test_query_vana_forest_cover_filtering():
    engine = FinVanaIntegrationEngine()
    
    # Query all
    res_all = engine.query_vana_forest_cover(consumer_actor="VANA")
    assert res_all["status"] == "SUCCESS"
    assert res_all["records_count"] == 5
    assert len(res_all["data_sha256"]) == 64

    # Query specific district
    res_pune = engine.query_vana_forest_cover(consumer_actor="VANA", district="Pune")
    assert res_pune["records_count"] == 1
    assert res_pune["records"][0]["district"] == "Pune"
    assert res_pune["records"][0]["total_forest_cover_km2"] == 1743.86

    # Non-existent district raises ValueError
    with pytest.raises(ValueError) as exc:
        engine.query_vana_forest_cover(consumer_actor="VANA", district="NonExistentDistrict")
    assert "No forest cover records found" in str(exc.value)


def test_query_vana_mangrove_biomass():
    engine = FinVanaIntegrationEngine()

    res_all = engine.query_vana_mangrove_biomass(consumer_actor="VANA")
    assert res_all["status"] == "SUCCESS"
    assert res_all["records_count"] == 5

    # Zone query
    res_airoli = engine.query_vana_mangrove_biomass(consumer_actor="VANA", zone_query="Airoli")
    assert res_airoli["records_count"] == 1
    assert "Airoli" in res_airoli["records"][0]["sanctuary_zone"]
    assert res_airoli["records"][0]["measured_agb_mg_per_ha"] == 84.83


def test_execute_fin_carbon_underwriting_forest():
    engine = FinVanaIntegrationEngine()
    req = CarbonUnderwritingRequest(
        project_id="PROJ-FIN-MAHA-01",
        underwriter_actor="FIN",
        target_dataset_id="DS-FSI-ISFR-2023-FOREST-COVER",
        target_district_or_plot="Thane",
        underwriting_purpose="ESG_CARBON_UNDERWRITING",
        carbon_price_usd_per_ton=30.0,
        project_lifespan_years=25,
        discount_rate_pct=5.0,
    )
    result = engine.execute_fin_carbon_underwriting(req)
    assert isinstance(result, CarbonUnderwritingResult)
    assert result.project_id == "PROJ-FIN-MAHA-01"
    assert result.target_area == "Thane"
    assert result.total_biomass_mg > 0.0
    assert result.carbon_stock_t_c > 0.0
    assert result.co2_equivalent_t_co2e > 0.0
    assert result.net_present_value_usd > 0.0
    assert result.esg_risk_rating == "AAA"
    assert len(result.evidence_hash) == 64


def test_execute_fin_carbon_underwriting_mangrove():
    engine = FinVanaIntegrationEngine()
    req = CarbonUnderwritingRequest(
        project_id="PROJ-FIN-MANGROVE-01",
        underwriter_actor="FIN",
        target_dataset_id="DS-THANECREEK-2023-BIOMASS",
        target_district_or_plot="Vashi",
        underwriting_purpose="BLUE_CARBON_QUANTIFICATION",
        carbon_price_usd_per_ton=35.0,
        project_lifespan_years=20,
        discount_rate_pct=6.0,
    )
    result = engine.execute_fin_carbon_underwriting(req)
    assert isinstance(result, CarbonUnderwritingResult)
    assert result.target_area == "Vashi"
    assert result.esg_risk_rating == "AAA"
    assert result.mdu_schema_ref == "mdu://ontology/environmental/v2.2/biomass.schema.json"


def test_fin_vana_catalog():
    engine = FinVanaIntegrationEngine()
    catalog = engine.get_catalog()
    assert "FIN" in catalog["integrated_systems"]
    assert "VANA" in catalog["integrated_systems"]
    assert catalog["total_forest_records"] == 5
    assert catalog["total_mangrove_records"] == 5
