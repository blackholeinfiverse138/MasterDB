"""
MasterDB Governance Service Layer
=================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
Authority: MasterDB Data Governance & Constitutional Controls

High-level domain service orchestrating deterministic rule evaluation,
optimistic concurrency control (OCC) state transitions, and Pravah streaming.
"""
from typing import Dict, Any, List, Optional
import logging
from evaluation_engine.rule_engine import MasterDBRuleEngine, EvaluationRubric, BiotechRuleEngine
from evaluation_engine.pravah_streaming import PravahReplayEngine, PravahEventType, PravahEvent
from task_selector.state_machine import ConcurrencyGovernanceEngine, GovernanceLifecycleState, ConcurrencyRecord
from canonical_db.db import CanonicalDB

logger = logging.getLogger("governance_service")


class GovernanceService:
    """Enterprise domain service managing the governance convergence lifecycle."""

    def __init__(
        self,
        rule_engine: Optional[MasterDBRuleEngine] = None,
        pravah_engine: Optional[PravahReplayEngine] = None,
        concurrency_engine: Optional[ConcurrencyGovernanceEngine] = None,
        canonical_db: Optional[CanonicalDB] = None
    ):
        self.rule_engine = rule_engine or MasterDBRuleEngine()
        self.pravah_engine = pravah_engine or PravahReplayEngine()
        self.concurrency_engine = concurrency_engine or ConcurrencyGovernanceEngine(pravah_engine=self.pravah_engine)
        self.canonical_db = canonical_db or CanonicalDB()

    def process_audit_submission(
        self,
        task_id: str = "T-GOV-F01",
        candidate_name: str = "Ansh Gupta",
        capability_name: str = "MasterDB Convergence",
        payload: Optional[Dict[str, Any]] = None,
        trace_id: str = "trace-gov-service",
        governance_dimension: Optional[str] = None,
        query_drug: Optional[str] = None,
        **kwargs: Any
    ) -> EvaluationRubric:
        """Executes full evaluation, logs Pravah event, and records state."""
        if payload is None:
            payload = {}
        # 1. Evaluate payload deterministically
        rubric = self.rule_engine.evaluate_candidate_submission(
            task_id=task_id,
            candidate_name=candidate_name,
            capability_name=capability_name,
            payload=payload,
            governance_dimension=governance_dimension,
            query_drug=query_drug,
            **kwargs
        )

        # 2. Log Pravah event
        event_type = PravahEventType.GOVERNANCE_GATE_EVAL
        self.pravah_engine.append_event(
            trace_id=trace_id,
            event_type=event_type,
            payload={
                "task_id": task_id,
                "candidate_name": candidate_name,
                "overall_pass": rubric.overall_pass,
                "score": rubric.score,
                "deterministic_hash": rubric.deterministic_hash
            },
            source_system="MASTERDB_GOVERNANCE_SERVICE",
            destination="PRAVAH_REPLAY_LEDGER"
        )

        # 3. Store in canonical DB
        try:
            self.canonical_db.store_review(
                review_id=f"rev-{trace_id}",
                candidate_id=candidate_name,
                status="pass" if rubric.overall_pass else "fail",
                score=int(rubric.score),
                decision="APPROVED" if rubric.overall_pass else "REJECTED",
                payload={
                    "task_id": task_id,
                    "capability": capability_name,
                    "rubric": rubric.model_dump()
                }
            )
        except Exception as e:
            logger.debug(f"CanonicalDB store review warning: {e}")

        return rubric

    def execute_occ_transition(
        self,
        entity_id: str,
        expected_version: int,
        target_state: GovernanceLifecycleState,
        actor: str,
        trace_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConcurrencyRecord:
        """Performs atomic OCC transition and emits state transition event."""
        record = self.concurrency_engine.transition_state(
            entity_id=entity_id,
            expected_version=expected_version,
            target_state=target_state,
            actor=actor,
            trace_id=trace_id,
            metadata=metadata or {}
        )
        return record
