"""
MasterDB Test Configuration and Shared Fixtures
================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from typing import Dict, Any
from fastapi.testclient import TestClient

from api.production import app, rule_engine, review_orchestrator, llm_client
from evaluation_engine.rule_engine import MasterDBRuleEngine, SensitivityLevel
from task_selector.review_orchestrator import MasterDBReviewOrchestrator
from integrations.local_llm_client import LocalLLMClient
from security.middleware import reset_spent_tokens


@pytest.fixture(autouse=True)
def clean_environment():
    """Resets global state and spent tokens before each test."""
    reset_spent_tokens()
    rule_engine.dataset_registry.clear()
    yield
    reset_spent_tokens()
    rule_engine.dataset_registry.clear()


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient with ErrorBoundaryMiddleware active."""
    return TestClient(app)


@pytest.fixture
def valid_dataset_payload() -> Dict[str, Any]:
    """Sample valid dataset payload compliant with MasterDB schema."""
    return {
        "dataset_id": "masterdb.spatial.survey_of_india.administrative_boundaries",
        "dataset_name": "Survey of India Administrative Boundaries",
        "source_system": "BharatMala-GIS",
        "category": "geospatial",
        "schema_contract": {
            "columns": [
                {"name": "state_code", "type": "string", "nullable": False},
                {"name": "district_code", "type": "string", "nullable": False},
                {"name": "geometry", "type": "geojson_polygon", "nullable": False},
                {"name": "area_sqkm", "type": "float", "nullable": True},
            ],
            "primary_key": ["state_code", "district_code"],
            "crs": "EPSG:4326",
        },
        "records_sample": [
            {
                "state_code": "MH",
                "district_code": "PUN",
                "geometry": {"type": "Polygon", "coordinates": [[[73.8, 18.5], [73.9, 18.5], [73.9, 18.6], [73.8, 18.5]]]},
                "area_sqkm": 15642.0,
            }
        ],
        "sensitivity_level": "RESTRICTED",
        "owner": "BharatMala Spatial Governance Team",
        "documentation_uri": "https://gov.bhiv.in/docs/spatial/soi-boundaries",
        "metadata": {
            "version": "1.4.0",
            "curator": "Ansh Gupta",
            "section16_compliant": True,
        },
    }


@pytest.fixture
def synthetic_dataset_payload() -> Dict[str, Any]:
    """Sample synthetic test fixture that must be quarantined."""
    return {
        "dataset_id": "mock_synthetic_dataset_fixture_01",
        "dataset_name": "Test Dummy Data",
        "source_system": "mock_generator",
        "category": "test_fixture",
        "schema_contract": {
            "columns": [{"name": "dummy_id", "type": "int"}],
        },
        "sensitivity_level": "PUBLIC",
        "owner": "Unit Tester",
    }
