"""
Strict Pydantic Schema Definitions for Biotech & MasterDB Governance
=====================================================================
All models enforce ConfigDict(extra="forbid") to eliminate schema_violation risks.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from evaluation_engine.pravah_streaming import PravahEventType
from task_selector.state_machine import GovernanceLifecycleState


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TargetDatabase(str, Enum):
    VECTOR_DB = "VectorDB"
    GRAPH_DB = "GraphDB"
    METADATA_DB = "MetadataDB"
    DOCUMENT_DB = "DocumentDB"
    TIME_SERIES_DB = "TimeSeriesDB"
    RELATIONAL_DB = "RelationalDB"
    ARCHIVE_DB = "ArchiveDB"
    ANALYTICS_DB = "AnalyticsDB"


class IngestionFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    PDF = "pdf"
    TXT = "txt"
    IMAGE = "image"


class IngestionJobStatus(str, Enum):
    PERSISTED = "PERSISTED"
    REJECTED = "REJECTED"
    PARTIAL_PERSISTENCE = "PARTIAL_PERSISTENCE"


class MasterDBValidationRequest(StrictBaseModel):
    dataset_path: str = Field(..., description="Path to dataset to validate")
    metadata_path: Optional[str] = Field(default=None, description="Path to companion metadata")
    dataset_id: Optional[str] = Field(default=None, description="Optional dataset ID")


class MasterDBCertificationRequest(StrictBaseModel):
    dataset_id: Optional[str] = Field(default=None, description="Target dataset ID")
    dataset_path: Optional[str] = Field(default=None, description="Path to dataset")
    metadata_path: Optional[str] = Field(default=None, description="Path to metadata")


class IngestJobStep(StrictBaseModel):
    step: str = Field(..., description="Ingestion pipeline step name")
    passed: bool = Field(..., description="Step execution outcome")
    detail: str = Field(..., description="Detailed step status or error")
    at: str = Field(..., description="ISO 8601 timestamp")


class MasterDBIngestRequest(StrictBaseModel):
    dataset_id: str = Field(..., min_length=3, max_length=128, description="Canonical dataset identifier")
    target_database: TargetDatabase = Field(..., description="Target database (e.g. RelationalDB, MetadataDB)")
    source_format: IngestionFormat = Field(..., description="Source data format (e.g. json, csv)")
    package_id: Optional[str] = Field(default=None, description="Knowledge package identifier")
    upload_id: Optional[str] = Field(default=None, description="Staged upload identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary ingestion metadata")


class MasterDBIngestJob(StrictBaseModel):
    job_id: str = Field(..., description="Unique ingestion job identifier")
    trace_id: str = Field(..., description="Distributed trace identifier")
    dataset_id: str = Field(..., description="Dataset identifier")
    target_database: TargetDatabase = Field(..., description="Target database")
    source_format: IngestionFormat = Field(..., description="Data format")
    package_id: Optional[str] = Field(default=None, description="Knowledge package identifier")
    actor: str = Field(..., description="Operator or service actor")
    roles: List[str] = Field(default_factory=list, description="Actor assigned roles")
    status: IngestionJobStatus = Field(..., description="Job final status")
    certification_state: Optional[str] = Field(default=None, description="Dataset certification state")
    integrity_score: Optional[float] = Field(default=None, description="Integrity audit score")
    steps: List[IngestJobStep] = Field(default_factory=list, description="Ordered step verification audit")
    rejection_reason: Optional[str] = Field(default=None, description="Rejection reason if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Job metadata")
    submitted_at: str = Field(..., description="Submission ISO 8601 timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion ISO 8601 timestamp")


class BiotechAuditRequest(StrictBaseModel):
    task_id: str = Field(..., min_length=3, max_length=100, description="Task identifier (e.g. T-GOV-F01)")
    candidate_name: str = Field(..., min_length=2, max_length=50, description="Candidate stream owner (e.g. Sara, Shamit)")
    capability_name: str = Field(..., min_length=3, max_length=100, description="Stream capability name")
    payload: Dict[str, Any] = Field(..., description="Audit observation payload")
    query_drug: Optional[str] = Field(default=None, description="Query drug for attribution testing")
    governance_dimension: Optional[str] = Field(default=None, description="Optional governance dimension")


class BiotechEvaluationRequest(StrictBaseModel):
    rule_name: str = Field(..., min_length=3, max_length=100, description="Name of rule to evaluate")
    payload: Dict[str, Any] = Field(..., description="Payload to evaluate against rule")


class DisagreementRecordRequest(StrictBaseModel):
    candidate_id: str = Field(..., min_length=3, max_length=100, description="Candidate ID receiving disagreement")
    raised_by: str = Field(..., min_length=2, max_length=50, description="Auditor raising dispute (e.g. ANSH)")
    reason: str = Field(..., min_length=5, max_length=255, description="Factual basis for dispute")
    dissenting_view: str = Field(..., min_length=5, max_length=1000, description="Technical dissenting finding")


class EntityExtractionRequest(StrictBaseModel):
    text: str = Field(..., min_length=3, max_length=5000, description="Biomedical or regulatory text to parse")
    query_id: Optional[str] = Field(default=None, description="Optional query tracking ID")


class PravahStreamEventRequest(StrictBaseModel):
    trace_id: str = Field(..., min_length=4, max_length=128, description="Distributed trace ID")
    event_type: PravahEventType = Field(..., description="Canonical Pravah event type")
    payload: Dict[str, Any] = Field(..., description="Event payload data")
    source_system: str = Field(default="BIOTECH", min_length=2, max_length=64, description="Originating system")
    destination: str = Field(default="PRAVAH_REPLAY_LEDGER", min_length=2, max_length=64, description="Target subsystem")


class PravahReplayRequest(StrictBaseModel):
    from_sequence: int = Field(default=1, ge=1, description="Start sequence for replay")
    to_sequence: Optional[int] = Field(default=None, ge=1, description="End sequence for replay")


class ConcurrencyTransitionRequest(StrictBaseModel):
    entity_id: str = Field(..., min_length=3, max_length=128, description="Unique entity identifier")
    expected_version: int = Field(..., ge=1, description="Expected OCC record version")
    target_state: GovernanceLifecycleState = Field(..., description="Target DFA lifecycle state")
    actor: str = Field(..., min_length=2, max_length=64, description="Transition operator")
    trace_id: str = Field(..., min_length=4, max_length=128, description="Trace identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary transition metadata")


class HealthResponse(StrictBaseModel):
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    active_capabilities: List[str] = Field(..., description="List of operational capability modules")
    error_boundary_active: bool = Field(..., description="Indicates zero-500 boundary status")


class MetricsResponse(StrictBaseModel):
    service: str = Field(..., description="Service identifier")
    total_reviews_initiated: int = Field(..., description="Count of reviews initiated")
    total_disagreements_recorded: int = Field(..., description="Count of Section 16 disagreements")
    deterministic_state_hash: str = Field(..., description="Canonical SHA-256 state hash proof")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")

MasterDBAuditRequest = BiotechAuditRequest
MasterDBEvaluationRequest = BiotechEvaluationRequest
