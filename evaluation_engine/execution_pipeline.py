"""
Biotech Execution Pipeline
==========================
End-to-end evaluation execution pipeline coordinating ingestion, rule-based audit gates,
Pravah replay event streaming, and Section 16 dispute management.
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timezone
from evaluation_engine.rule_engine import BiotechRuleEngine, EvaluationRubric
from evaluation_engine.pravah_streaming import PravahReplayEngine, PravahEventType
from task_selector.review_orchestrator import (
    BiotechReviewOrchestrator,
    CandidateReviewRecord,
    DecisionState,
    ReviewPacketContract
)
from task_selector.state_machine import ConcurrencyGovernanceEngine, GovernanceLifecycleState

logger = logging.getLogger("execution_pipeline")


class BiotechExecutionPipeline:
    """Production execution pipeline coordinating deterministic evaluation stages."""

    def __init__(
        self,
        rule_engine: Optional[BiotechRuleEngine] = None,
        review_orchestrator: Optional[BiotechReviewOrchestrator] = None,
        pravah_engine: Optional[PravahReplayEngine] = None,
        concurrency_engine: Optional[ConcurrencyGovernanceEngine] = None
    ):
        self.rule_engine = rule_engine or BiotechRuleEngine()
        self.review_orchestrator = review_orchestrator or BiotechReviewOrchestrator()
        self.pravah_engine = pravah_engine or PravahReplayEngine()
        self.concurrency_engine = concurrency_engine or ConcurrencyGovernanceEngine(pravah_engine=self.pravah_engine)

    def execute_evaluation(
        self,
        task_id: str,
        candidate_name: str,
        capability_name: str,
        payload: Dict[str, Any],
        trace_id: str,
        query_drug: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs candidate audit through all pipeline stages."""
        logger.info(f"[PIPELINE] Starting execution for candidate={candidate_name}, task={task_id}, trace={trace_id}")

        # Stage 1: Rule Engine Evaluation
        rubric = self.rule_engine.evaluate_candidate_submission(
            task_id=task_id,
            candidate_name=candidate_name,
            capability_name=capability_name,
            payload=payload,
            query_drug=query_drug
        )

        # Stage 2: Pravah Event Streaming
        event_type = PravahEventType.GOVERNANCE_GATE_EVAL
        pravah_event = self.pravah_engine.append_event(
            trace_id=trace_id,
            event_type=event_type,
            payload={
                "task_id": task_id,
                "candidate_name": candidate_name,
                "score": rubric.score,
                "overall_pass": rubric.overall_pass,
                "hash": rubric.deterministic_hash
            },
            source_system="BIOTECH_PIPELINE",
            destination="PRAVAH_REPLAY_LEDGER"
        )

        # Stage 3: Orchestrator Review Record Update
        contract = ReviewPacketContract(
            candidate_name=candidate_name,
            capability_name=capability_name,
            entry_point="api/production.py",
            core_execution_flow="BiotechExecutionPipeline.execute_evaluation",
            runtime_flow="PravahReplayEngine.append_event",
            real_output=payload,
            what_changed="Parikshak remediation interoperability validation",
            failure_cases=["OCC lock contention", "Pravah replay divergence"],
            test_results={"score": rubric.score, "overall_pass": rubric.overall_pass},
            integration_contract="JSON schema v1.0 strict forbid",
            known_limitations=[],
            evidence_uris=[f"pravah://event/{pravah_event.event_id}"]
        )
        review_record = self.review_orchestrator.start_candidate_review(
            candidate_name=candidate_name,
            capability=capability_name,
            packet_contract=contract
        )

        if not rubric.overall_pass:
            review_record = self.review_orchestrator.finalize_decision(
                review_id=review_record.review_id,
                final_decision=DecisionState.REJECTED
            )
        else:
            review_record = self.review_orchestrator.finalize_decision(
                review_id=review_record.review_id,
                final_decision=DecisionState.APPROVED
            )

        return {
            "evaluation_result": "PASS" if rubric.overall_pass else "FAIL",
            "score": rubric.score,
            "failure_type": None if rubric.overall_pass else "incomplete",
            "deterministic_hash": rubric.deterministic_hash,
            "trace_id": trace_id,
            "pravah_sequence": pravah_event.sequence,
            "review_record": review_record.model_dump()
        }


# Global pipeline singleton
execution_pipeline = BiotechExecutionPipeline()
