"""
Enums for Interface Test types and statuses.
Provides type-safe values aligned with database check constraints.
"""

from enum import Enum


class InterfaceType(str, Enum):
    """
    Valid interface test types per AS1851-2012.
    Must match the check constraint in database migration 007.
    """
    MANUAL_OVERRIDE = "manual_override"
    ALARM_COORDINATION = "alarm_coordination"
    SHUTDOWN_SEQUENCE = "shutdown_sequence"
    SPRINKLER_ACTIVATION = "sprinkler_activation"


class SessionStatus(str, Enum):
    """
    Valid session lifecycle statuses.
    Must match the check constraint in database migration 007.
    """
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VALIDATED = "validated"


class ComplianceOutcome(str, Enum):
    """
    Valid compliance outcomes for interface tests.
    Must match the check constraint in database migration 007.
    """
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"


class EventType(str, Enum):
    """Common event types for interface test timeline."""
    START = "start"
    OBSERVATION = "observation"
    RESPONSE_DETECTED = "response_detected"
    VALIDATION = "validation"
    COMPLETION = "completion"
    ERROR = "error"
