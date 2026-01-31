"""
Integration sync log model for auditing data synchronization operations.

Tracks all sync operations between the CDP and external systems,
providing visibility into data flows and enabling troubleshooting.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Text, Index, Integer, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class SyncType(str, Enum):
    """Types of synchronization operations."""
    INITIAL = "initial"           # First-time full sync
    INCREMENTAL = "incremental"   # Delta sync since last run
    FULL = "full"                 # Complete refresh
    REALTIME = "realtime"         # Event-driven sync
    MANUAL = "manual"             # User-triggered sync
    SCHEDULED = "scheduled"       # Cron-triggered sync


class SyncStatus(str, Enum):
    """Status of sync operations."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"           # Some records failed
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class SyncDirection(str, Enum):
    """Direction of data flow."""
    INBOUND = "inbound"           # External -> CDP
    OUTBOUND = "outbound"         # CDP -> External
    BIDIRECTIONAL = "bidirectional"


class IntegrationSyncLog(Base):
    """
    Integration sync log for auditing data synchronization.
    
    Provides comprehensive tracking of:
    - Sync operation metadata (type, direction, timing)
    - Record counts (processed, created, updated, failed)
    - Error details and diagnostics
    - Performance metrics
    """
    
    # Integration reference
    integration_id = Column(String(12), ForeignKey("integrations.id"), nullable=False, index=True)
    
    # Sync operation metadata
    sync_type = Column(
        SQLEnum(SyncType),
        nullable=False,
        index=True
    )
    sync_direction = Column(
        SQLEnum(SyncDirection),
        nullable=False
    )
    status = Column(
        SQLEnum(SyncStatus),
        default=SyncStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Entity being synced
    entity_type = Column(String(100), nullable=False)  # contacts, leads, events, etc.
    
    # Record counts
    records_processed = Column(Integer, default=0, nullable=False)
    records_created = Column(Integer, default=0, nullable=False)
    records_updated = Column(Integer, default=0, nullable=False)
    records_failed = Column(Integer, default=0, nullable=False)
    records_skipped = Column(Integer, default=0, nullable=False)
    
    # Detailed record tracking
    # Example: {
    #     "created_ids": ["id1", "id2"],
    #     "updated_ids": ["id3"],
    #     "failed_records": [{"id": "id4", "error": "Validation failed"}]
    # }
    record_details = Column(JSON, default=dict, nullable=False)
    
    # Timing
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Error details
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, default=dict, nullable=False)
    # Example: {
    #     "error_type": "APIError",
    #     "error_code": "RATE_LIMIT_EXCEEDED",
    #     "retryable": true,
    #     "stack_trace": "..."
    # }
    
    # Sync configuration used
    sync_config_snapshot = Column(JSON, default=dict, nullable=False)
    
    # Performance metrics
    api_calls_made = Column(Integer, default=0, nullable=False)
    api_calls_failed = Column(Integer, default=0, nullable=False)
    bytes_transferred = Column(Integer, default=0, nullable=False)
    
    # Rate limiting encountered
    rate_limit_hits = Column(Integer, default=0, nullable=False)
    rate_limit_wait_seconds = Column(Float, default=0.0, nullable=False)
    
    # User who triggered (null for scheduled)
    triggered_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    
    # Celery task ID for background jobs
    celery_task_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    integration = relationship("Integration", back_populates="sync_logs")
    user = relationship("User", foreign_keys=[triggered_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_sync_log_integration_started', 'integration_id', 'started_at'),
        Index('idx_sync_log_status_entity', 'status', 'entity_type'),
        Index('idx_sync_log_date_range', 'started_at', 'completed_at'),
    )
    
    def complete(self, status: SyncStatus) -> None:
        """Mark sync as completed with status."""
        self.status = status
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def record_success(self, created: int = 0, updated: int = 0, skipped: int = 0) -> None:
        """Record successful record operations."""
        self.records_created += created
        self.records_updated += updated
        self.records_skipped += skipped
        self.records_processed += created + updated + skipped
    
    def record_failure(self, record_id: str, error: str) -> None:
        """Record a failed record."""
        self.records_failed += 1
        self.records_processed += 1
        
        if "failed_records" not in self.record_details:
            self.record_details["failed_records"] = []
        
        self.record_details["failed_records"].append({
            "id": record_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def record_api_call(self, success: bool = True, bytes_count: int = 0) -> None:
        """Record an API call."""
        self.api_calls_made += 1
        if not success:
            self.api_calls_failed += 1
        self.bytes_transferred += bytes_count
    
    def record_rate_limit(self, wait_seconds: float) -> None:
        """Record a rate limit hit."""
        self.rate_limit_hits += 1
        self.rate_limit_wait_seconds += wait_seconds
    
    def set_error(self, error_type: str, error_code: str, message: str, retryable: bool = False) -> None:
        """Set error details."""
        self.error_message = message
        self.error_details = {
            "error_type": error_type,
            "error_code": error_code,
            "retryable": retryable,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.records_processed == 0:
            return 100.0
        successful = self.records_processed - self.records_failed
        return (successful / self.records_processed) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "integration_id": self.integration_id,
            "sync_type": self.sync_type.value if self.sync_type else None,
            "sync_direction": self.sync_direction.value if self.sync_direction else None,
            "status": self.status.value if self.status else None,
            "entity_type": self.entity_type,
            "records_processed": self.records_processed,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "records_skipped": self.records_skipped,
            "success_rate": round(self.get_success_rate(), 2),
            "record_details": self.record_details,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "api_calls_made": self.api_calls_made,
            "api_calls_failed": self.api_calls_failed,
            "bytes_transferred": self.bytes_transferred,
            "rate_limit_hits": self.rate_limit_hits,
            "triggered_by": self.triggered_by,
            "celery_task_id": self.celery_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
