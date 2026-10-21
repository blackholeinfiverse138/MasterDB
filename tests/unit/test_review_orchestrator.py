"""
Unit Tests - MasterDB Review Orchestrator & Section 16 Protocol
==============================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from task_selector.review_orchestrator import (
    MasterDBReviewOrchestrator,
    ReviewStage,
    DecisionState,
    Section16Disagreement,
    ReviewPacketContract,
)


def test_orchestrator_initialization():
    orchestrator = MasterDBReviewOrchestrator()
    assert len(orchestrator.standard_datasets) >= 2
    assert "DS-FSI-ISFR-2023-FOREST-COVER" in orchestrator.standard_datasets
    assert "DS-THANECREEK-2023-BIOMASS" in orchestrator.standard_datasets


def test_build_review_packet_canonical():
    orchestrator = MasterDBReviewOrchestrator()
    packet = orchestrator.build_review_packet(
        task_id="T-GOV-F01",
        candidate_name="Ansh Gupta",
        dataset_id="DS-FSI-ISFR-2023-FOREST-COVER"
    )
    assert isinstance(packet, ReviewPacketContract)
    assert packet.candidate_name == "Ansh Gupta"
    assert packet.rubric.composite_score >= 75.0
    assert packet.decision_state == DecisionState.APPROVED
    assert len(packet.state_hash) == 64


def test_advance_stage_sequence():
    orchestrator = MasterDBReviewOrchestrator()
    stage1 = ReviewStage.STAGE_1_FUNCTIONAL_TESTING
    stage2 = orchestrator.advance_stage(stage1)
    assert stage2 == ReviewStage.STAGE_2_TECHNICAL_REVIEW
    stage3 = orchestrator.advance_stage(stage2)
    assert stage3 == ReviewStage.STAGE_3_INDEPENDENT_AUDIT
    
    # Advancing last stage stays at last stage
    stage9 = ReviewStage.STAGE_9_HANDOVER
    assert orchestrator.advance_stage(stage9) == stage9


def test_section16_disagreement_registration_and_resolution():
    orchestrator = MasterDBReviewOrchestrator()
    assert len(orchestrator.active_disagreements) == 0

    disagreement = Section16Disagreement(
        observation="Schema field 'spatial_resolution' lacked ISO precision metadata",
        evidence="Observed raw float coordinate bounding boxes without datum reference",
        differing_interpretation="Developer considered standard WGS84 implicit",
        required_verification="Explicit EPSG code registration required",
    )
    orchestrator.register_disagreement(disagreement)
    assert len(orchestrator.active_disagreements) == 1
    assert orchestrator.active_disagreements[0].resolved is False

    # Resolve disagreement
    resolved = orchestrator.resolve_disagreement(
        index=0,
        resolution_notes="Explicit EPSG:4326 geometry validation added and verified by Ansh Gupta"
    )
    assert resolved is True
    assert orchestrator.active_disagreements[0].resolved is True
    assert "EPSG:4326" in orchestrator.active_disagreements[0].resolution_notes


def test_execute_review_stage_with_section16_unacknowledged():
    orchestrator = MasterDBReviewOrchestrator()
    packet = orchestrator.execute_review_stage(
        review_id="REV-2026-TEST-001",
        stage=ReviewStage.STAGE_3_INDEPENDENT_AUDIT,
        candidate_name="Candidate X",
        dataset_ids=["DS-FSI-ISFR-2023-FOREST-COVER"],
        section16_acknowledged=False,
    )
    assert packet.decision_state == DecisionState.REVISION_REQUIRED
    assert len(packet.disagreements) >= 1
    assert "unacknowledged Section 16" in packet.disagreements[-1].observation
