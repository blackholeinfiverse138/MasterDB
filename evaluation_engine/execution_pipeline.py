"""
MasterDB Convergence Execution Pipeline
=======================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
Authority: MasterDB Data Governance & Constitutional Controls

End-to-end evaluation execution pipeline coordinating ingestion, rule-based audit gates,
Pravah replay event streaming, and Section 16 dispute management.
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timezone
from evaluation_engine.rule_engine import MasterDBRuleEngine, EvaluationRubric, BiotechRuleEngine
from evaluation_engine.pravah_streaming import PravahReplayEngine, PravahEventType
from task_selector.review_orchestrator import (
    MasterDBReviewOrchestrator,
    CandidateReviewRecord,
    DecisionState,
    ReviewPacketContract,
    BiotechReviewOrchestrator
)
from task_selector.state_machine import ConcurrencyGovernanceEngine, GovernanceLifecycleState
from canonical_db.db import CanonicalDB

logger = logging.getLogger("execution_pipeline")


class MasterDBExecutionPipeline:
    """Production execution pipeline coordinating deterministic evaluation stages."""

    def __init__(
        self,
        rule_engine: Optional[MasterDBRuleEngine] = None,
        review_orchestrator: Optional[MasterDBReviewOrchestrator] = None,
        pravah_engine: Optional[PravahReplayEngine] = None,
        concurrency_engine: Optional[ConcurrencyGovernanceEngine] = None,
        canonical_db: Optional[CanonicalDB] = None
    ):
        self.rule_engine = rule_engine or MasterDBRuleEngine()
        self.review_orchestrator = review_orchestrator or MasterDBReviewOrchestrator()
        self.pravah_engine = pravah_engine or PravahReplayEngine()
        self.concurrency_engine = concurrency_engine or ConcurrencyGovernanceEngine(pravah_engine=self.pravah_engine)
        self.canonical_db = canonical_db or CanonicalDB()

    def execute_evaluation(
        self,
        task_id: str = "T-GOV-F01",
        candidate_name: str = "Ansh Gupta",
        capability_name: str = "MasterDB Convergence",
        payload: Optional[Dict[str, Any]] = None,
        trace_id: str = "trace-direct-execution",
        governance_dimension: Optional[str] = None,
        query_drug: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Runs candidate audit through all pipeline stages."""
        if payload is None:
            payload = {}
        logger.info(f"[PIPELINE] Starting execution for candidate={candidate_name}, task={task_id}, trace={trace_id}")

        # Stage 1: Rule Engine Evaluation
        rubric = self.rule_engine.evaluate_candidate_submission(
            task_id=task_id,
            candidate_name=candidate_name,
            capability_name=capability_name,
            payload=payload,
            governance_dimension=governance_dimension,
            query_drug=query_drug,
            **kwargs
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
            source_system="MASTERDB_PIPELINE",
            destination="PRAVAH_REPLAY_LEDGER"
        )

        # Stage 3: Orchestrator Review Record Update
        contract = ReviewPacketContract(
            candidate_name=candidate_name,
            capability_name=capability_name,
            entry_point="api/production.py",
            core_execution_flow="MasterDBExecutionPipeline.execute_evaluation",
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

        # Stage 4: Persist Review to Canonical DB
        try:
            self.canonical_db.store_review(
                review_id=review_record.review_id,
                candidate_id=candidate_name,
                status="pass" if rubric.overall_pass else "fail",
                score=int(rubric.score),
                decision=review_record.decision_state.value if hasattr(review_record.decision_state, "value") else str(review_record.decision_state),
                payload=payload
            )
        except Exception as e:
            logger.debug(f"CanonicalDB store review warning: {e}")

        return {
            "evaluation_result": "PASS" if rubric.overall_pass else "FAIL",
            "score": rubric.score,
            "failure_type": None if rubric.overall_pass else "incomplete",
            "deterministic_hash": rubric.deterministic_hash,
            "trace_id": trace_id,
            "pravah_sequence": pravah_event.sequence,
            "review_record": review_record.model_dump()
        }


# Canonical class & backward compatibility alias
BiotechExecutionPipeline = MasterDBExecutionPipeline

# Global pipeline singleton
execution_pipeline = MasterDBExecutionPipeline()
